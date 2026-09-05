export default {
  async fetch(request, env) {
    return handleRequest(request, env);
  }
};

async function handleRequest(request, env) {
  const url = new URL(request.url);
  const pathname = url.pathname;

  if (request.method === 'OPTIONS') {
    return new Response(null, {
      status: 204,
      headers: corsHeaders()
    });
  }

  if (!pathname.startsWith('/api/')) {
    return fetch(request);
  }

  try {
    await ensureTables(env);

    if (pathname === '/api/auth/register' && request.method === 'POST') {
      return await handleRegister(request, env);
    }

    if (pathname === '/api/auth/login' && request.method === 'POST') {
      return await handleLogin(request, env);
    }

    if (pathname === '/api/usuarios/verificar-o-crear' && request.method === 'POST') {
      return await verifyOrCreateUsuario(request, env);
    }

    const usuarioMatch = pathname.match(/^\/api\/usuarios\/([^/]+)$/);
    if (usuarioMatch && request.method === 'GET') {
      return await getUsuario(usuarioMatch[1], env);
    }
    if (usuarioMatch && request.method === 'PUT') {
      return await updateUsuario(usuarioMatch[1], request, env);
    }

    const contactosUsuarioMatch = pathname.match(/^\/api\/usuarios\/([^/]+)\/contactos$/);
    if (contactosUsuarioMatch && request.method === 'GET') {
      return await getContactosUsuario(contactosUsuarioMatch[1], env);
    }
    if (contactosUsuarioMatch && request.method === 'POST') {
      return await createContacto(contactosUsuarioMatch[1], request, env);
    }

    const contactoMatch = pathname.match(/^\/api\/contactos\/([^/]+)$/);
    if (contactoMatch && request.method === 'PUT') {
      return await updateContacto(contactoMatch[1], request, env);
    }
    if (contactoMatch && request.method === 'DELETE') {
      return await deleteContacto(contactoMatch[1], env);
    }

    return jsonResponse({ error: 'API route not found' }, 404);
  } catch (err) {
    return jsonResponse({ error: String(err) }, 500);
  }
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization'
  };
}

function jsonResponse(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'Content-Type': 'application/json;charset=UTF-8',
      ...corsHeaders()
    }
  });
}

async function ensureTables(env) {
  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS Usuario (
      usuario_id TEXT PRIMARY KEY,
      usuario_nombre TEXT,
      usuario_email TEXT UNIQUE,
      usuario_telefono TEXT,
      usuario_activo INTEGER,
      usuario_familiar_nombre TEXT,
      usuario_familiar_telefono TEXT,
      usuario_password TEXT
    );
  `).run();

  // Migrations for existing databases with older schema
  await safeAlter(env.DB, 'ALTER TABLE Usuario ADD COLUMN usuario_password TEXT');
  await safeAlter(env.DB, 'ALTER TABLE Usuario ADD COLUMN usuario_familiar_nombre TEXT');
  await safeAlter(env.DB, 'ALTER TABLE Usuario ADD COLUMN usuario_familiar_telefono TEXT');

  await env.DB.prepare(`
    CREATE TABLE IF NOT EXISTS Contacto_Emergencia (
      contacto_id TEXT PRIMARY KEY,
      usuario_id TEXT NOT NULL,
      contacto_nombre TEXT NOT NULL,
      contacto_telefono TEXT,
      contacto_estado INTEGER,
      FOREIGN KEY (usuario_id) REFERENCES Usuario(usuario_id)
    );
  `).run();

  await safeAlter(env.DB, 'ALTER TABLE Contacto_Emergencia ADD COLUMN contacto_estado INTEGER');
}

async function safeAlter(db, sql) {
  try {
    await db.prepare(sql).run();
  } catch (_) {
    // Ignore "duplicate column" and similar migration-safe errors.
  }
}

async function tableExists(db, tableName) {
  const row = await db.prepare(`
    SELECT name
    FROM sqlite_master
    WHERE type = 'table' AND name = ?
    LIMIT 1
  `).bind(tableName).first();

  return Boolean(row);
}

function toHex(buffer) {
  return Array.from(new Uint8Array(buffer)).map(b => b.toString(16).padStart(2,'0')).join('');
}

async function derivePBKDF2(password, saltHex) {
  const enc = new TextEncoder();
  const salt = hexToUint8(saltHex);
  const keyMaterial = await crypto.subtle.importKey('raw', enc.encode(password), {name:'PBKDF2'}, false, ['deriveBits']);
  const params = {name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256'};
  const derived = await crypto.subtle.deriveBits(params, keyMaterial, 256);
  return toHex(derived);
}

function hexToUint8(hex) {
  if (hex.length % 2 !== 0) hex = '0' + hex;
  const arr = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) arr[i/2] = parseInt(hex.substr(i,2), 16);
  return arr;
}

function genSaltHex() {
  const arr = crypto.getRandomValues(new Uint8Array(16));
  return Array.from(arr).map(b => b.toString(16).padStart(2,'0')).join('');
}

async function handleRegister(request, env) {
  const db = env.DB;
  if (!db) return jsonResponse({error: 'Database binding not found (DB).'}, 500);

  const body = await request.json();
  const email = (body.email || '').toLowerCase().trim();
  const nombre = body.nombre || 'Usuario';
  const password = body.password || '';
  if (!email || !password) return jsonResponse({error: 'email y password son requeridos'}, 400);

  // Check existing
  const existing = await db.prepare('SELECT usuario_id FROM Usuario WHERE usuario_email = ?').bind(email).first();
  if (existing) return jsonResponse({error: 'Usuario ya existe'}, 409);

  const salt = genSaltHex();
  const hash = await derivePBKDF2(password, salt);
  const stored = `${salt}$${hash}`;
  const usuario_id = crypto.randomUUID();

  await db.prepare(`INSERT INTO Usuario (usuario_id, usuario_nombre, usuario_email, usuario_telefono, usuario_activo, usuario_familiar_nombre, usuario_familiar_telefono, usuario_password) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`)
    .bind(usuario_id, nombre, email, '', 1, '', '', stored)
    .run();

  return jsonResponse({usuario_id, mensaje: 'Usuario creado exitosamente'}, 201);
}

async function handleLogin(request, event) {
  const db = event.DB;
  if (!db) return jsonResponse({error: 'Database binding not found (DB).'}, 500);

  const body = await request.json();
  const email = (body.email || '').toLowerCase().trim();
  const password = body.password || '';
  if (!email || !password) return jsonResponse({error: 'email y password son requeridos'}, 400);

  const row = await db.prepare('SELECT usuario_id, usuario_password FROM Usuario WHERE usuario_email = ? LIMIT 1').bind(email).first();
  if (!row) return jsonResponse({error: 'Credenciales inválidas'}, 401);
  const usuario_id = row.usuario_id;
  const stored = row.usuario_password;
  if (!stored) return jsonResponse({error: 'Usuario no tiene contraseña establecida'}, 401);

  const parts = stored.split('$');
  if (parts.length !== 2) return jsonResponse({error: 'Hash de contraseña en formato inválido'}, 500);
  const salt = parts[0];
  const hash = parts[1];
  const derived = await derivePBKDF2(password, salt);
  if (derived !== hash) return jsonResponse({error: 'Credenciales inválidas'}, 401);

  return jsonResponse({usuario_id, mensaje: 'Login exitoso'}, 200);
}

async function verifyOrCreateUsuario(request, env) {
  const body = await request.json();
  const email = (body.email || '').toLowerCase().trim();
  const nombre = (body.nombre || 'Usuario').trim() || 'Usuario';

  if (!email) {
    return jsonResponse({ error: 'Email es requerido' }, 400);
  }

  const existing = await env.DB.prepare(`
    SELECT usuario_id
    FROM Usuario
    WHERE usuario_email = ?
    LIMIT 1
  `).bind(email).first();

  if (existing) {
    return jsonResponse({
      usuario_id: existing.usuario_id,
      estado: 'existente',
      mensaje: 'Usuario ya existe'
    }, 200);
  }

  const usuarioId = crypto.randomUUID();

  await env.DB.prepare(`
    INSERT INTO Usuario (
      usuario_id,
      usuario_nombre,
      usuario_email,
      usuario_telefono,
      usuario_activo,
      usuario_familiar_nombre,
      usuario_familiar_telefono,
      usuario_password
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
  `).bind(usuarioId, nombre, email, '', 1, '', '', null).run();

  return jsonResponse({
    usuario_id: usuarioId,
    estado: 'creado',
    mensaje: 'Usuario creado exitosamente'
  }, 201);
}

async function getUsuario(usuarioId, env) {
  const row = await env.DB.prepare(`
    SELECT
      usuario_id,
      usuario_nombre,
      usuario_email,
      usuario_telefono,
      usuario_activo,
      usuario_familiar_nombre,
      usuario_familiar_telefono
    FROM Usuario
    WHERE usuario_id = ?
    LIMIT 1
  `).bind(usuarioId).first();

  if (!row) {
    return jsonResponse({ error: 'Usuario no encontrado' }, 404);
  }

  return jsonResponse({
    usuario_id: row.usuario_id,
    nombre: row.usuario_nombre,
    email: row.usuario_email,
    telefono: row.usuario_telefono,
    activo: Boolean(row.usuario_activo),
    familiar_nombre: row.usuario_familiar_nombre,
    familiar_telefono: row.usuario_familiar_telefono
  }, 200);
}

async function updateUsuario(usuarioId, request, env) {
  const body = await request.json();
  const nombre = body.nombre ?? null;
  const telefono = body.telefono ?? null;
  const familiarNombre = body.familiar_nombre ?? null;
  const familiarTelefono = body.familiar_telefono ?? null;

  const exists = await env.DB.prepare('SELECT usuario_id FROM Usuario WHERE usuario_id = ? LIMIT 1').bind(usuarioId).first();
  if (!exists) {
    return jsonResponse({ error: 'Usuario no encontrado' }, 404);
  }

  await env.DB.prepare(`
    UPDATE Usuario
    SET
      usuario_nombre = COALESCE(?, usuario_nombre),
      usuario_telefono = COALESCE(?, usuario_telefono),
      usuario_familiar_nombre = COALESCE(?, usuario_familiar_nombre),
      usuario_familiar_telefono = COALESCE(?, usuario_familiar_telefono)
    WHERE usuario_id = ?
  `).bind(nombre, telefono, familiarNombre, familiarTelefono, usuarioId).run();

  return jsonResponse({ mensaje: 'Usuario actualizado correctamente', usuario_id: usuarioId }, 200);
}

async function getContactosUsuario(usuarioId, env) {
  const result = await env.DB.prepare(`
    SELECT
      contacto_id,
      usuario_id,
      contacto_nombre,
      contacto_telefono,
      contacto_estado
    FROM Contacto_Emergencia
    WHERE usuario_id = ?
    ORDER BY contacto_nombre ASC
  `).bind(usuarioId).all();

  const rows = result.results || [];
  const contactos = rows.map((row) => ({
    contacto_id: row.contacto_id,
    usuario_id: row.usuario_id,
    nombre: row.contacto_nombre,
    telefono: row.contacto_telefono,
    estado: Boolean(row.contacto_estado)
  }));

  return jsonResponse({ contactos, total: contactos.length }, 200);
}

async function createContacto(usuarioId, request, env) {
  const body = await request.json();
  const nombre = (body.nombre || '').trim();
  const telefono = (body.telefono || '').trim();
  const estado = body.estado === false ? 0 : 1;

  if (!nombre || !telefono) {
    return jsonResponse({ error: 'nombre y telefono son requeridos' }, 400);
  }

  const usuario = await env.DB.prepare('SELECT usuario_id FROM Usuario WHERE usuario_id = ? LIMIT 1').bind(usuarioId).first();
  if (!usuario) {
    return jsonResponse({ error: 'Usuario no encontrado' }, 404);
  }

  // Idempotencia: evita duplicados cuando el cliente reintenta o hace doble clic en guardar.
  const existente = await env.DB.prepare(`
    SELECT contacto_id
    FROM Contacto_Emergencia
    WHERE usuario_id = ?
      AND contacto_nombre = ?
      AND contacto_telefono = ?
    LIMIT 1
  `).bind(usuarioId, nombre, telefono).first();

  if (existente) {
    return jsonResponse({
      contacto_id: existente.contacto_id,
      mensaje: 'Contacto ya existente'
    }, 200);
  }

  const contactoId = crypto.randomUUID();

  await env.DB.prepare(`
    INSERT INTO Contacto_Emergencia (
      contacto_id,
      usuario_id,
      contacto_nombre,
      contacto_telefono,
      contacto_estado
    ) VALUES (?, ?, ?, ?, ?)
  `).bind(contactoId, usuarioId, nombre, telefono, estado).run();

  return jsonResponse({ contacto_id: contactoId, mensaje: 'Contacto creado exitosamente' }, 201);
}

async function updateContacto(contactoId, request, env) {
  const body = await request.json();
  const nombre = body.nombre ?? null;
  const telefono = body.telefono ?? null;
  const estado = body.estado;
  const estadoDb = estado === undefined || estado === null ? null : (estado ? 1 : 0);

  const existing = await env.DB.prepare('SELECT contacto_id FROM Contacto_Emergencia WHERE contacto_id = ? LIMIT 1').bind(contactoId).first();
  if (!existing) {
    return jsonResponse({ error: 'Contacto no encontrado' }, 404);
  }

  await env.DB.prepare(`
    UPDATE Contacto_Emergencia
    SET
      contacto_nombre = COALESCE(?, contacto_nombre),
      contacto_telefono = COALESCE(?, contacto_telefono),
      contacto_estado = COALESCE(?, contacto_estado)
    WHERE contacto_id = ?
  `).bind(nombre, telefono, estadoDb, contactoId).run();

  return jsonResponse({ mensaje: 'Contacto actualizado correctamente', contacto_id: contactoId }, 200);
}

async function deleteContacto(contactoId, env) {
  const existing = await env.DB.prepare('SELECT contacto_id FROM Contacto_Emergencia WHERE contacto_id = ? LIMIT 1').bind(contactoId).first();
  if (!existing) {
    return jsonResponse({ error: 'Contacto no encontrado' }, 404);
  }

  // Si hay notificaciones ligadas al contacto, se eliminan primero para no romper FK.
  if (await tableExists(env.DB, 'Notificacion')) {
    await env.DB.prepare('DELETE FROM Notificacion WHERE contacto_id = ?').bind(contactoId).run();
  }

  await env.DB.prepare('DELETE FROM Contacto_Emergencia WHERE contacto_id = ?').bind(contactoId).run();
  return jsonResponse({ mensaje: 'Contacto eliminado correctamente', contacto_id: contactoId }, 200);
}
