import sqlite3
import os
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, g

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Users ---

def get_user_by_username(username):
    return get_db().execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()

def create_user(username, password):
    db = get_db()
    db.execute(
        'INSERT INTO users (username, password_hash) VALUES (?, ?)',
        (username, generate_password_hash(password))
    )
    db.commit()

def verify_password(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def count_users():
    return get_db().execute('SELECT COUNT(*) FROM users').fetchone()[0]

# --- Servers ---

def get_all_servers(active_only=True):
    q = 'SELECT * FROM servers'
    if active_only:
        q += ' WHERE active = 1'
    q += ' ORDER BY type, hostname'
    return get_db().execute(q).fetchall()

def get_server(server_id):
    return get_db().execute(
        'SELECT * FROM servers WHERE id = ?', (server_id,)
    ).fetchone()

def create_server(hostname, ip, type_, ssh_user, ssh_port, cert_dest_dir, post_deploy_cmd):
    db = get_db()
    db.execute(
        '''INSERT INTO servers
           (hostname, ip, type, ssh_user, ssh_port, cert_dest_dir, post_deploy_cmd)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (hostname, ip, type_, ssh_user, ssh_port, cert_dest_dir, post_deploy_cmd)
    )
    db.commit()

def update_server(server_id, hostname, ip, type_, ssh_user, ssh_port, cert_dest_dir, post_deploy_cmd):
    db = get_db()
    db.execute(
        '''UPDATE servers SET hostname=?, ip=?, type=?, ssh_user=?, ssh_port=?,
           cert_dest_dir=?, post_deploy_cmd=? WHERE id=?''',
        (hostname, ip, type_, ssh_user, ssh_port, cert_dest_dir, post_deploy_cmd, server_id)
    )
    db.commit()

def delete_server(server_id):
    db = get_db()
    db.execute('UPDATE servers SET active = 0 WHERE id = ?', (server_id,))
    db.commit()

def get_server_last_deploy(server_id):
    return get_db().execute(
        '''SELECT * FROM deploy_logs
           WHERE server_id = ? AND status != 'running'
           ORDER BY started_at DESC LIMIT 1''',
        (server_id,)
    ).fetchone()

# --- Deploy logs ---

def create_deploy_log(server_id, server_hostname, trigger='auto'):
    db = get_db()
    cur = db.execute(
        '''INSERT INTO deploy_logs (server_id, server_hostname, status, trigger)
           VALUES (?, ?, 'running', ?)''',
        (server_id, server_hostname, trigger)
    )
    db.commit()
    return cur.lastrowid

def finish_deploy_log(log_id, status, output):
    db = get_db()
    db.execute(
        '''UPDATE deploy_logs SET status=?, output=?, finished_at=CURRENT_TIMESTAMP
           WHERE id=?''',
        (status, output, log_id)
    )
    db.commit()

def get_deploy_logs(limit=100):
    return get_db().execute(
        '''SELECT dl.*, s.type as server_type
           FROM deploy_logs dl
           LEFT JOIN servers s ON dl.server_id = s.id
           ORDER BY dl.started_at DESC LIMIT ?''',
        (limit,)
    ).fetchall()

def get_recent_failures():
    return get_db().execute(
        '''SELECT COUNT(*) FROM deploy_logs
           WHERE status = 'error'
           AND started_at >= datetime('now', '-7 days')'''
    ).fetchone()[0]

# --- Settings ---

def get_setting(key, default=None):
    row = get_db().execute(
        'SELECT value FROM settings WHERE key = ?', (key,)
    ).fetchone()
    return row['value'] if row else default

def set_setting(key, value):
    db = get_db()
    db.execute(
        '''INSERT INTO settings (key, value, updated_at)
           VALUES (?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP''',
        (key, value)
    )
    db.commit()

def get_all_settings():
    rows = get_db().execute('SELECT key, value FROM settings').fetchall()
    return {row['key']: row['value'] for row in rows}
