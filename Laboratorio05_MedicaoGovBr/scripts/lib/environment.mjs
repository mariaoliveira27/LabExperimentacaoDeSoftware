// Condições da máquina de medição que o módulo os do Node não expõe: o plano de energia ativo e o
// adaptador de rede da rota padrão (Ethernet ou Wi-Fi, velocidade do link, físico ou virtual; um
// adaptador virtual indica VPN ativa). Gravado uma vez por sessão em data/run-metadata.json.
//
// Nada aqui identifica a rede ou a pessoa: não se lê endereço IP, MAC, nome da rede (SSID) nem
// provedor. Provedor e cidade são registrados à mão (docs/proposta.md, seção 6.6).
import { execFile } from 'node:child_process';
import { readFile, readdir, access } from 'node:fs/promises';
import { promisify } from 'node:util';

const run = promisify(execFile);
const OPTS = { timeout: 15_000, windowsHide: true };

// Windows: GUID e nome do esquema de energia ativo. O texto em volta muda com o idioma do sistema
// ("Power Scheme GUID" / "GUID do Esquema de Energia"), então só o GUID e o nome entre parênteses
// são lidos.
export function parsePowercfg(stdout) {
  const m = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*\(([^)]+)\)/i.exec(stdout);
  return m ? { guid: m[1].toLowerCase(), name: m[2].trim() } : null;
}

const WINDOWS_NETWORK_PS = `
$ErrorActionPreference = 'SilentlyContinue'
$best = Get-NetRoute -DestinationPrefix '0.0.0.0/0' |
  ForEach-Object { [pscustomobject]@{ ifIndex = $_.ifIndex; metric = $_.RouteMetric + (Get-NetIPInterface -InterfaceIndex $_.ifIndex -AddressFamily IPv4).InterfaceMetric } } |
  Sort-Object metric | Select-Object -First 1
$a = if ($best) { Get-NetAdapter -InterfaceIndex $best.ifIndex } else { $null }
[pscustomobject]@{
  defaultRouteAdapter = if ($a) { [pscustomobject]@{ description = $a.InterfaceDescription; physicalMediaType = $a.PhysicalMediaType; linkSpeed = $a.LinkSpeed; virtual = [bool]$a.Virtual } } else { $null }
  batteries = @(Get-CimInstance Win32_Battery).Count
} | ConvertTo-Json -Compress -Depth 3
`;

async function windowsInfo() {
  const out = {};
  try {
    const { stdout } = await run('powercfg', ['/getactivescheme'], OPTS);
    out.powerPlan = parsePowercfg(stdout) ?? { unparsed: stdout.trim() };
  } catch (err) {
    out.powerPlan = { error: err.message };
  }
  try {
    const { stdout } = await run('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command', WINDOWS_NETWORK_PS], OPTS);
    const parsed = JSON.parse(stdout.trim());
    out.network = parsed.defaultRouteAdapter ?? { error: 'nenhuma rota padrão IPv4 encontrada' };
    // Um desktop sem bateria está sempre na tomada; em notebook isso precisa ser conferido à mão.
    out.batteries = parsed.batteries;
  } catch (err) {
    out.network = { error: err.message };
  }
  return out;
}

async function linuxInfo() {
  const out = {};
  try {
    const governor = (await readFile('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'utf8')).trim();
    let profile = null;
    try {
      profile = (await readFile('/sys/firmware/acpi/platform_profile', 'utf8')).trim();
    } catch {
      // nem toda máquina expõe esse arquivo
    }
    out.powerPlan = { cpuGovernor: governor, platformProfile: profile };
  } catch (err) {
    out.powerPlan = { error: err.message };
  }
  try {
    // /proc/net/route: a rota padrão tem Destination 00000000; escolhe a de menor métrica.
    const rows = (await readFile('/proc/net/route', 'utf8')).trim().split('\n').slice(1).map((l) => l.trim().split(/\s+/));
    const def = rows.filter((c) => c[1] === '00000000').sort((a, b) => Number(a[6]) - Number(b[6]))[0];
    if (!def) throw new Error('nenhuma rota padrão IPv4 encontrada');
    const iface = def[0];
    const exists = (p) => access(p).then(() => true, () => false);
    const wireless = await exists(`/sys/class/net/${iface}/wireless`);
    const physical = await exists(`/sys/class/net/${iface}/device`);
    let speed = null;
    try {
      speed = Number((await readFile(`/sys/class/net/${iface}/speed`, 'utf8')).trim());
    } catch {
      // adaptadores Wi-Fi em geral não informam a velocidade aqui
    }
    out.network = { interface: iface, type: wireless ? 'wifi' : 'wired-or-other', virtual: !physical, linkSpeedMbps: speed };
    const ps = await readdir('/sys/class/power_supply').catch(() => []);
    out.batteries = ps.filter((n) => n.startsWith('BAT')).length;
  } catch (err) {
    out.network = { error: err.message };
  }
  return out;
}

export async function hostConditions(platform = process.platform) {
  if (platform === 'win32') return windowsInfo();
  if (platform === 'linux') return linuxInfo();
  return { powerPlan: null, network: null, note: `não capturado automaticamente em ${platform}; registrar à mão` };
}
