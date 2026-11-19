// GET HTTPS mínimo usado pelo robots-check.mjs.
//
// Por que não fetch(): alguns hosts do gov.br enviam só o certificado final e omitem o
// intermediário. Navegadores (e portanto o Lighthouse/Chrome) contornam isso baixando o
// intermediário pela URL "CA Issuers" (AIA) do certificado; o Node não faz isso e falha com
// UNABLE_TO_VERIFY_LEAF_SIGNATURE. fetchMissingIntermediate() reproduz o comportamento do navegador
// sem desligar a verificação: o intermediário baixado só é aceito se a assinatura dele for
// verificada contra uma raiz do repositório de confiança do Node.
import http from 'node:http';
import https from 'node:https';
import tls from 'node:tls';
import { X509Certificate } from 'node:crypto';

const REDIRECT_CODES = new Set([301, 302, 303, 307, 308]);
const MAX_BODY_BYTES = 512 * 1024; // A RFC 9309 pede que o parser aceite pelo menos 500 KiB.

/**
 * GET em `url`, seguindo até `maxRedirects` redirecionamentos (a RFC 9309 pede pelo menos cinco).
 * @returns {Promise<{status:number, finalUrl:string, body:string}>}
 */
export function httpGet(url, { userAgent, ca, timeoutMs = 20_000, maxRedirects = 5 } = {}) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https:') ? https : http;
    const options = { headers: { 'user-agent': userAgent, accept: 'text/plain,*/*;q=0.8' }, timeout: timeoutMs };
    if (ca && mod === https) options.ca = ca;
    const req = mod.get(url, options, (res) => {
      const { statusCode, headers } = res;
      if (REDIRECT_CODES.has(statusCode) && headers.location && maxRedirects > 0) {
        res.resume();
        const next = new URL(headers.location, url).href;
        resolve(httpGet(next, { userAgent, ca, timeoutMs, maxRedirects: maxRedirects - 1 }));
        return;
      }
      const chunks = [];
      let size = 0;
      res.on('data', (c) => {
        size += c.length;
        if (size <= MAX_BODY_BYTES) chunks.push(c);
      });
      res.on('end', () => resolve({ status: statusCode, finalUrl: url, body: Buffer.concat(chunks).toString('utf8') }));
      res.on('error', reject);
    });
    req.on('timeout', () => req.destroy(Object.assign(new Error(`tempo esgotado após ${timeoutMs} ms`), { code: 'ETIMEDOUT' })));
    req.on('error', reject);
  });
}

function getBuffer(url, timeoutMs = 15_000) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https:') ? https : http;
    const req = mod.get(url, { timeout: timeoutMs }, (res) => {
      if (res.statusCode !== 200) {
        res.resume();
        reject(new Error(`download do certificado (AIA) devolveu HTTP ${res.statusCode}`));
        return;
      }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    });
    req.on('timeout', () => req.destroy(new Error('tempo esgotado no download do certificado (AIA)')));
    req.on('error', reject);
  });
}

/** Lê o certificado final do servidor. Nenhum dado da aplicação é enviado nesta conexão. */
function readLeafCertificate(host) {
  return new Promise((resolve, reject) => {
    const sock = tls.connect({ host, port: 443, servername: host, rejectUnauthorized: false }, () => {
      const cert = sock.getPeerCertificate();
      sock.end();
      resolve(cert);
    });
    sock.setTimeout(15_000, () => sock.destroy(new Error('tempo esgotado no handshake TLS')));
    sock.on('error', reject);
  });
}

/**
 * Baixa o certificado intermediário que o servidor deixou de enviar e confere que ele foi
 * assinado por uma raiz do repositório de confiança do Node.
 * @returns {Promise<{ca:string[], note:string}>} Lista de CAs para repetir a requisição.
 */
export async function fetchMissingIntermediate(host) {
  const leaf = await readLeafCertificate(host);
  const issuerUrl = leaf.infoAccess?.['CA Issuers - URI']?.[0];
  if (!issuerUrl) throw new Error('o certificado final não tem URL "CA Issuers" (AIA)');
  const raw = await getBuffer(issuerUrl);
  const intermediate = new X509Certificate(raw); // aceita DER ou PEM
  const roots = tls.rootCertificates.map((pem) => new X509Certificate(pem));
  const root = roots.find((r) => intermediate.checkIssued(r) && intermediate.verify(r.publicKey));
  if (!root) throw new Error(`o intermediário "${intermediate.subject}" não foi assinado por uma raiz confiável`);
  const cn = (dn) => dn.split('\n').find((l) => l.startsWith('CN='))?.slice(3) ?? dn;
  return {
    ca: [...tls.rootCertificates, intermediate.toString()],
    note: `servidor não enviou o intermediário; "${cn(intermediate.subject)}" baixado de ${issuerUrl} e verificado contra a raiz "${cn(root.subject)}"`,
  };
}
