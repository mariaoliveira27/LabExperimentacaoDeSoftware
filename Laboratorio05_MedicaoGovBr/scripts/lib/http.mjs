// Minimal HTTPS GET used by robots-check.mjs.
//
// Why not fetch(): some gov.br hosts send only their leaf certificate and omit the
// intermediate. Browsers (and therefore Lighthouse/Chrome) recover by downloading the
// intermediate from the certificate's AIA "CA Issuers" URL; Node does not, and fails with
// UNABLE_TO_VERIFY_LEAF_SIGNATURE. fetchMissingIntermediate() reproduces the browser behavior
// while keeping verification on: the downloaded intermediate is only accepted if its
// signature verifies against a root in Node's built-in trust store.
import http from 'node:http';
import https from 'node:https';
import tls from 'node:tls';
import { X509Certificate } from 'node:crypto';

const REDIRECT_CODES = new Set([301, 302, 303, 307, 308]);
const MAX_BODY_BYTES = 512 * 1024; // RFC 9309 asks parsers to handle at least 500 KiB.

/**
 * GET `url`, following up to `maxRedirects` redirects (RFC 9309 asks for at least five).
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
    req.on('timeout', () => req.destroy(Object.assign(new Error(`timeout after ${timeoutMs} ms`), { code: 'ETIMEDOUT' })));
    req.on('error', reject);
  });
}

function getBuffer(url, timeoutMs = 15_000) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith('https:') ? https : http;
    const req = mod.get(url, { timeout: timeoutMs }, (res) => {
      if (res.statusCode !== 200) {
        res.resume();
        reject(new Error(`AIA download returned HTTP ${res.statusCode}`));
        return;
      }
      const chunks = [];
      res.on('data', (c) => chunks.push(c));
      res.on('end', () => resolve(Buffer.concat(chunks)));
      res.on('error', reject);
    });
    req.on('timeout', () => req.destroy(new Error('AIA download timeout')));
    req.on('error', reject);
  });
}

/** Reads the server's leaf certificate. No application data is sent on this connection. */
function readLeafCertificate(host) {
  return new Promise((resolve, reject) => {
    const sock = tls.connect({ host, port: 443, servername: host, rejectUnauthorized: false }, () => {
      const cert = sock.getPeerCertificate();
      sock.end();
      resolve(cert);
    });
    sock.setTimeout(15_000, () => sock.destroy(new Error('TLS handshake timeout')));
    sock.on('error', reject);
  });
}

/**
 * Downloads the intermediate certificate the server failed to send and checks that a root
 * in Node's trust store signed it.
 * @returns {Promise<{ca:string[], note:string}>} CA list to retry the request with.
 */
export async function fetchMissingIntermediate(host) {
  const leaf = await readLeafCertificate(host);
  const issuerUrl = leaf.infoAccess?.['CA Issuers - URI']?.[0];
  if (!issuerUrl) throw new Error('leaf certificate has no AIA CA Issuers URL');
  const raw = await getBuffer(issuerUrl);
  const intermediate = new X509Certificate(raw); // accepts DER or PEM
  const roots = tls.rootCertificates.map((pem) => new X509Certificate(pem));
  const root = roots.find((r) => intermediate.checkIssued(r) && intermediate.verify(r.publicKey));
  if (!root) throw new Error(`intermediate "${intermediate.subject}" is not signed by a trusted root`);
  const cn = (dn) => dn.split('\n').find((l) => l.startsWith('CN='))?.slice(3) ?? dn;
  return {
    ca: [...tls.rootCertificates, intermediate.toString()],
    note: `server omitted intermediate; "${cn(intermediate.subject)}" downloaded from ${issuerUrl} and verified against root "${cn(root.subject)}"`,
  };
}
