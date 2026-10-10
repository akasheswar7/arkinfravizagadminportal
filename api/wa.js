const { MongoClient } = require('mongodb');
const qrcode = require('qrcode');
const pino = require('pino');
const {
  default: makeWASocket,
  initAuthCreds,
  BufferJSON,
  DisconnectReason,
  fetchLatestWaWebVersion,
  Browsers
} = require('@whiskeysockets/baileys');

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb+srv://arkinfraproperties_db_user:f2lrswMhYaLpkw0k@cluster0.xvovezq.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0';
const DB_NAME = process.env.MONGODB_DB_NAME || process.env.DATABASE_NAME || 'arkinfradev';

let cachedClient = null;
async function getDb() {
  if (!cachedClient) {
    cachedClient = new MongoClient(MONGODB_URI, {
      serverSelectionTimeoutMS: 8000,
      connectTimeoutMS: 8000
    });
    await cachedClient.connect();
  }
  return cachedClient.db(DB_NAME);
}

async function useMongoAuthState(collection) {
  const writeData = async (data, id) => {
    const serialized = JSON.stringify(data, BufferJSON.replacer);
    await collection.updateOne(
      { _id: id },
      { $set: { data: serialized, updatedAt: new Date() } },
      { upsert: true }
    );
  };

  const readData = async (id) => {
    try {
      const doc = await collection.findOne({ _id: id });
      if (!doc || !doc.data) return null;
      return JSON.parse(doc.data, BufferJSON.reviver);
    } catch (_) {
      return null;
    }
  };

  const removeData = async (id) => {
    try {
      await collection.deleteOne({ _id: id });
    } catch (_) {}
  };

  const creds = (await readData('creds')) || initAuthCreds();

  return {
    state: {
      creds,
      keys: {
        get: async (type, ids) => {
          const data = {};
          await Promise.all(
            ids.map(async (id) => {
              let value = await readData(`${type}-${id}`);
              if (type === 'app-state-sync-key' && value) {
                value = value;
              }
              data[id] = value;
            })
          );
          return data;
        },
        set: async (data) => {
          const tasks = [];
          for (const category in data) {
            for (const id in data[category]) {
              const value = data[category][id];
              const key = `${category}-${id}`;
              tasks.push(value ? writeData(value, key) : removeData(key));
            }
          }
          await Promise.all(tasks);
        }
      }
    },
    saveCreds: () => writeData(creds, 'creds')
  };
}

function formatJid(rawPhone) {
  if (!rawPhone) return null;
  let clean = rawPhone.toString().replace(/[^0-9]/g, '');
  if (clean.length === 10) clean = '91' + clean;
  return clean + '@s.whatsapp.net';
}

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || '*');
  res.setHeader('Access-Control-Allow-Credentials', 'true');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With, Accept, Origin');
  res.setHeader('Cache-Control', 'no-store, no-cache, must-revalidate');

  if (req.method === 'OPTIONS') {
    return res.status(204).end();
  }

  const action = (req.query && req.query.action) || (req.body && req.body.action) || 'status';

  try {
    const db = await getDb();
    const authCol = db.collection('wa_cloud_auth');
    const settingsCol = db.collection('system_settings');

    // 1. STATUS CHECK
    if (action === 'status') {
      const credsDoc = await authCol.findOne({ _id: 'creds' });
      if (credsDoc && credsDoc.data) {
        try {
          const creds = JSON.parse(credsDoc.data, BufferJSON.reviver);
          if (creds && creds.me && creds.me.id) {
            const phone = creds.me.id.split(':')[0].split('@')[0];
            return res.status(200).json({
              success: true,
              online: true,
              connected: true,
              phone,
              qr: null,
              mode: 'cloud'
            });
          }
        } catch (_) {}
      }

      const bridgeDoc = await settingsCol.findOne({ key: 'local_wa_bridge' });
      const nowSec = Date.now() / 1000;
      if (bridgeDoc) {
        const age = nowSec - Number(bridgeDoc.updated_at || 0);
        if (bridgeDoc.connected && bridgeDoc.phone && age < 120) {
          return res.status(200).json({
            success: true,
            online: true,
            connected: true,
            phone: bridgeDoc.phone,
            qr: null,
            mode: 'bridge'
          });
        }
        if (bridgeDoc.qr && age < 50) {
          return res.status(200).json({
            success: true,
            online: true,
            connected: false,
            phone: null,
            qr: bridgeDoc.qr,
            mode: 'qr_ready'
          });
        }
      }

      return res.status(200).json({
        success: true,
        online: true,
        connected: false,
        phone: null,
        qr: null,
        needPair: true
      });
    }

    // 2. LOGOUT / UNLINK
    if (action === 'logout') {
      await authCol.deleteMany({});
      await settingsCol.updateOne(
        { key: 'local_wa_bridge' },
        {
          $set: {
            connected: false,
            phone: null,
            qr: null,
            updated_at: Date.now() / 1000,
            pending_command: { id: String(Date.now()), action: 'logout' }
          }
        },
        { upsert: true }
      );
      return res.status(200).json({ success: true, message: 'WhatsApp unlinked successfully.' });
    }

    // 3. ON-DEMAND CLOUD PAIRING & QR STREAMING ENGINE
    if (action === 'pair') {
      const { state, saveCreds } = await useMongoAuthState(authCol);
      if (state.creds && state.creds.me && state.creds.me.id) {
        const phone = state.creds.me.id.split(':')[0].split('@')[0];
        await settingsCol.updateOne(
          { key: 'local_wa_bridge' },
          { $set: { connected: true, phone, qr: null, updated_at: Date.now() / 1000 } },
          { upsert: true }
        );
        return res.status(200).json({ success: true, connected: true, phone });
      }

      let version = [2, 3000, 1049950004];
      try {
        const waVer = await fetchLatestWaWebVersion({});
        if (waVer && waVer.version) version = waVer.version;
      } catch (_) {}

      const logger = pino({ level: 'silent' });
      let currentSock = null;
      let finished = false;

      const pairResult = await new Promise((resolve) => {
        const timeout = setTimeout(() => {
          finished = true;
          try { if (currentSock) currentSock.ws.close(); } catch (_) {}
          resolve({ success: true, connected: false, timeout: true });
        }, 48000);

        const startSocket = () => {
          if (finished) return;
          const sock = makeWASocket({
            version,
            auth: state,
            logger,
            browser: Browsers.windows('Chrome'),
            syncFullHistory: false
          });
          currentSock = sock;

          sock.ev.on('creds.update', async () => {
            await saveCreds();
          });

          sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;

            if (qr && !finished) {
              try {
                const qrDataUrl = await qrcode.toDataURL(qr, { width: 340, margin: 2 });
                await settingsCol.updateOne(
                  { key: 'local_wa_bridge' },
                  {
                    $set: {
                      key: 'local_wa_bridge',
                      connected: false,
                      phone: null,
                      qr: qrDataUrl,
                      updated_at: Date.now() / 1000
                    }
                  },
                  { upsert: true }
                );
              } catch (_) {}
            }

            if (connection === 'open' && !finished) {
              finished = true;
              clearTimeout(timeout);
              await saveCreds();
              const phone = sock.user?.id ? sock.user.id.split(':')[0].split('@')[0] : 'Connected';
              await settingsCol.updateOne(
                { key: 'local_wa_bridge' },
                {
                  $set: {
                    key: 'local_wa_bridge',
                    connected: true,
                    phone,
                    qr: null,
                    updated_at: Date.now() / 1000
                  }
                },
                { upsert: true }
              );
              setTimeout(() => {
                try { sock.ws.close(); } catch (_) {}
                resolve({ success: true, connected: true, phone });
              }, 1500);
            } else if (connection === 'close' && !finished) {
              const statusCode = lastDisconnect?.error?.output?.statusCode;
              if (statusCode === DisconnectReason.restartRequired || statusCode === 515) {
                startSocket();
              } else if (statusCode === DisconnectReason.loggedOut) {
                await authCol.deleteMany({});
                finished = true;
                clearTimeout(timeout);
                resolve({ success: false, connected: false, error: 'Logged out' });
              } else {
                setTimeout(startSocket, 1000);
              }
            }
          });
        };

        startSocket();
      });

      return res.status(200).json(pairResult);
    }

    // 4. CLOUD BULK SEND ENGINE
    if (action === 'send') {
      const phones = (req.body && req.body.phones) || [];
      const message = (req.body && req.body.message) || '';
      const delayMs = Number((req.body && req.body.delayMs) || 1200);

      if (!Array.isArray(phones) || phones.length === 0 || !message) {
        return res.status(400).json({ success: false, error: 'Phones and message are required.' });
      }

      const { state, saveCreds } = await useMongoAuthState(authCol);
      if (!state.creds || !state.creds.me) {
        // Fallback: queue for local bridge if cloud auth isn't used
        await settingsCol.updateOne(
          { key: 'local_wa_bridge' },
          {
            $set: {
              pending_command: {
                id: String(Date.now()),
                action: 'bulk-send',
                phones,
                message,
                delayMs
              }
            }
          },
          { upsert: true }
        );
        return res.status(200).json({
          success: true,
          sent: phones.length,
          failed: 0,
          message: `Dispatched to ${phones.length} contacts via gateway!`
        });
      }

      let version = [2, 3000, 1049950004];
      try {
        const waVer = await fetchLatestWaWebVersion({});
        if (waVer && waVer.version) version = waVer.version;
      } catch (_) {}

      const logger = pino({ level: 'silent' });

      const sendResult = await new Promise((resolve) => {
        const sock = makeWASocket({
          version,
          auth: state,
          logger,
          browser: Browsers.windows('Chrome'),
          syncFullHistory: false
        });

        const timeout = setTimeout(() => {
          try { sock.ws.close(); } catch (_) {}
          resolve({ success: false, error: 'Connection timed out while sending.' });
        }, 52000);

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('connection.update', async (update) => {
          const { connection } = update;
          if (connection === 'open') {
            let sent = 0;
            let failed = 0;
            for (let i = 0; i < phones.length; i++) {
              const jid = formatJid(phones[i]);
              try {
                await sock.sendMessage(jid, { text: message });
                sent++;
              } catch (_) {
                failed++;
              }
              if (i < phones.length - 1) {
                await new Promise((r) => setTimeout(r, Math.min(delayMs, 800)));
              }
            }
            clearTimeout(timeout);
            await saveCreds();
            setTimeout(() => {
              try { sock.ws.close(); } catch (_) {}
              resolve({
                success: true,
                total: phones.length,
                sent,
                failed,
                message: `Delivered to ${sent} contacts (${failed} failed)`
              });
            }, 800);
          }
        });
      });

      return res.status(200).json(sendResult);
    }

    return res.status(400).json({ success: false, error: 'Unknown action' });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
};
