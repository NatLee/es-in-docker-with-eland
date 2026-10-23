import https from 'node:https';
import { readFileSync } from 'node:fs';
import { setTimeout as sleep } from 'node:timers/promises';

const { ELASTIC_PASSWORD, KIBANA_PASSWORD } = process.env;
if (!ELASTIC_PASSWORD || !KIBANA_PASSWORD) {
  throw new Error('ELASTIC_PASSWORD and KIBANA_PASSWORD must be set.');
}
const ca = readFileSync('/usr/share/kibana/config/certs/ca/ca.crt');
// Serialize passwords as JSON, never interpolate them into shell commands.
const body = JSON.stringify({ password: KIBANA_PASSWORD });

function setPassword() {
  return new Promise((resolve, reject) => {
    const request = https.request({
      hostname: 'backend-elasticsearch', port: 9200,
      path: '/_security/user/kibana_system/_password', method: 'POST', ca,
      auth: `elastic:${ELASTIC_PASSWORD}`,
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) },
    }, (response) => {
      response.resume();
      response.on('error', reject);
      response.on('end', () => {
        if (response.statusCode === 200) resolve();
        else reject(new Error(`Password setup returned HTTP ${response.statusCode}`));
      });
    });
    request.setTimeout(10000, () => request.destroy(new Error('Password setup timed out')));
    request.on('error', reject);
    request.end(body);
  });
}

for (let attempt = 1; attempt <= 6; attempt++) {
  try {
    await setPassword();
    console.log('kibana_system password configured');
    break;
  } catch (error) {
    if (attempt === 6) throw error;
    console.error(`Kibana setup attempt ${attempt} failed; retrying.`);
    await sleep(2000);
  }
}
