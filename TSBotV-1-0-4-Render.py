import socket
import time
import re
from datetime import datetime, timedelta
from collections import deque, defaultdict
import threading
import os
import sys

# Flask for web control panel
from flask import Flask, jsonify, render_template_string, request

# ============================================
# FLASK WEB CONTROL PANEL
# ============================================
app = Flask(__name__)

# Global bot instance
bot_instance = None
bot_lock = threading.Lock()

# HTML Template for control panel
CONTROL_PANEL_HTML = """
<!DOCTYPE html>
<html dir="ltr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TS Bot Control Panel</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .status {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            margin-bottom: 30px;
            font-size: 1.2em;
            font-weight: bold;
        }
        .status.online {
            background: rgba(0, 255, 0, 0.1);
            border: 2px solid #00ff00;
            color: #00ff00;
        }
        .status.offline {
            background: rgba(255, 0, 0, 0.1);
            border: 2px solid #ff0000;
            color: #ff0000;
        }
        .status.restarting {
            background: rgba(255, 165, 0, 0.1);
            border: 2px solid #ffa500;
            color: #ffa500;
        }
        .buttons {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        .btn {
            padding: 15px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }
        .btn:active {
            transform: translateY(0);
        }
        .btn-start {
            background: #00c853;
            color: white;
            grid-column: span 2;
        }
        .btn-start:hover {
            background: #00e676;
        }
        .btn-stop {
            background: #ff1744;
            color: white;
        }
        .btn-stop:hover {
            background: #ff5252;
        }
        .btn-restart {
            background: #ff9100;
            color: white;
        }
        .btn-restart:hover {
            background: #ffab40;
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .info {
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.03);
            border-radius: 10px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .info h3 {
            margin-bottom: 15px;
            color: #aaa;
        }
        .info-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .info-item:last-child {
            border-bottom: none;
        }
        .info-label {
            color: #888;
        }
        .info-value {
            color: #fff;
            font-weight: bold;
        }
        .response {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        .response.success {
            display: block;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            color: #00ff00;
        }
        .response.error {
            display: block;
            background: rgba(255, 0, 0, 0.1);
            border: 1px solid #ff0000;
            color: #ff0000;
        }
        .emoji {
            font-size: 3em;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="emoji">🤖</div>
            <h1>TeamSpeak Bot</h1>
            <p>Control Panel</p>
        </div>

        <div class="status {{ status_class }}">
            {{ status_text }}
        </div>

        <div class="buttons">
            <button class="btn btn-start" onclick="action('start')" {{ 'disabled' if status == 'online' else '' }}>
                ▶ Start Bot
            </button>
            <button class="btn btn-stop" onclick="action('stop')" {{ 'disabled' if status == 'offline' else '' }}>
                ⏹ Stop Bot
            </button>
            <button class="btn btn-restart" onclick="action('restart')" {{ 'disabled' if status == 'offline' else '' }}>
                🔄 Restart Bot
            </button>
        </div>

        <div id="response" class="response"></div>

        <div class="info">
            <h3>📊 Bot Information</h3>
            <div class="info-item">
                <span class="info-label">Status</span>
                <span class="info-value">{{ status_text }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Server</span>
                <span class="info-value">{{ server_ip }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Nickname</span>
                <span class="info-value">{{ nickname }}</span>
            </div>
            <div class="info-item">
                <span class="info-label">Uptime</span>
                <span class="info-value">{{ uptime }}</span>
            </div>
        </div>
    </div>

    <script>
        async function action(type) {
            const responseDiv = document.getElementById('response');
            responseDiv.className = 'response';
            responseDiv.style.display = 'none';

            try {
                const response = await fetch('/api/' + type, { method: 'POST' });
                const data = await response.json();
                
                responseDiv.className = 'response ' + (data.success ? 'success' : 'error');
                responseDiv.textContent = data.message;
                
                if (data.success) {
                    setTimeout(() => location.reload(), 2000);
                }
            } catch (error) {
                responseDiv.className = 'response error';
                responseDiv.textContent = 'Error: ' + error.message;
            }
        }

        // Auto refresh every 10 seconds
        setInterval(() => {
            fetch('/api/status')
                .then(res => res.json())
                .then(data => {
                    if (data.status !== '{{ status }}') {
                        location.reload();
                    }
                })
                .catch(() => {});
        }, 10000);
    </script>
</body>
</html>
"""

bot_start_time = None
bot_status = "offline"  # offline, online, restarting

def get_bot_info():
    """Get current bot information"""
    global bot_instance, bot_status, bot_start_time
    
    info = {
        'status': bot_status,
        'server_ip': SERVER_IP if 'SERVER_IP' in globals() else 'N/A',
        'nickname': BOT_NICKNAME if 'BOT_NICKNAME' in globals() else 'Staff',
        'uptime': 'N/A'
    }
    
    if bot_start_time and bot_status == 'online':
        uptime_seconds = int(time.time() - bot_start_time)
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        info['uptime'] = f"{hours}h {minutes}m {seconds}s"
    
    return info

@app.route('/')
def index():
    """Main control panel page"""
    info = get_bot_info()
    
    status_class = {
        'online': 'online',
        'offline': 'offline',
        'restarting': 'restarting'
    }.get(info['status'], 'offline')
    
    status_text = {
        'online': '🟢 Bot is Online',
        'offline': '🔴 Bot is Offline',
        'restarting': '🟠 Bot is Restarting...'
    }.get(info['status'], '⚪ Unknown')
    
    return render_template_string(
        CONTROL_PANEL_HTML,
        status=info['status'],
        status_class=status_class,
        status_text=status_text,
        server_ip=info['server_ip'],
        nickname=info['nickname'],
        uptime=info['uptime']
    )

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "bot": bot_status})

@app.route('/api/status')
def api_status():
    """API: Get bot status"""
    return jsonify(get_bot_info())

@app.route('/api/start', methods=['POST'])
def api_start():
    """API: Start the bot"""
    global bot_instance, bot_status, bot_start_time
    
    with bot_lock:
        if bot_status == 'online':
            return jsonify({
                'success': False,
                'message': '⚠️ Bot is already running!'
            })
        
        try:
            bot_status = 'restarting'
            
            # Start bot in a new thread
            def start_bot():
                global bot_instance, bot_status, bot_start_time
                try:
                    bot_instance = TeamSpeakBot(
                        host=SERVER_IP,
                        port=QUERY_PORT,
                        username=QUERY_USER,
                        password=QUERY_PASS,
                        server_id=SERVER_ID,
                        nickname=BOT_NICKNAME
                    )
                    bot_start_time = time.time()
                    bot_status = 'online'
                    
                    print("\n📋 Channels:")
                    channels = bot_instance.get_channel_list()
                    for name, cid in channels.items():
                        print(f"   CID {cid}: \"{name}\"")
                    
                    print("\n📋 Server Groups:")
                    groups = bot_instance.get_server_groups()
                    for sgid, name in groups.items():
                        print(f"   SGID {sgid}: \"{name}\"")
                    
                    bot_instance.monitor()
                except Exception as e:
                    print(f"❌ Bot error: {e}")
                    bot_status = 'offline'
                    bot_instance = None
            
            bot_thread = threading.Thread(target=start_bot, daemon=True)
            bot_thread.start()
            
            # Wait a bit to see if connection succeeds
            time.sleep(3)
            
            if bot_status == 'online':
                return jsonify({
                    'success': True,
                    'message': '✅ Bot started successfully!'
                })
            elif bot_status == 'restarting':
                # Still connecting
                return jsonify({
                    'success': True,
                    'message': '🔄 Bot is connecting... Please wait.'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '❌ Bot failed to start! Check logs.'
                })
                
        except Exception as e:
            bot_status = 'offline'
            return jsonify({
                'success': False,
                'message': f'❌ Error: {str(e)}'
            })

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """API: Stop the bot"""
    global bot_instance, bot_status, bot_start_time
    
    with bot_lock:
        if bot_status == 'offline':
            return jsonify({
                'success': False,
                'message': '⚠️ Bot is already stopped!'
            })
        
        try:
            if bot_instance:
                bot_instance.disconnect()
                bot_instance = None
            
            bot_status = 'offline'
            bot_start_time = None
            
            return jsonify({
                'success': True,
                'message': '🛑 Bot stopped successfully!'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'❌ Error stopping bot: {str(e)}'
            })

@app.route('/api/restart', methods=['POST'])
def api_restart():
    """API: Restart the bot"""
    global bot_instance, bot_status, bot_start_time
    
    with bot_lock:
        if bot_status == 'offline':
            return jsonify({
                'success': False,
                'message': '⚠️ Bot is not running! Start it first.'
            })
        
        try:
            # Stop current bot
            if bot_instance:
                bot_instance.disconnect()
                bot_instance = None
            
            bot_status = 'restarting'
            
            # Start new bot
            def restart_bot():
                global bot_instance, bot_status, bot_start_time
                try:
                    time.sleep(2)  # Wait for cleanup
                    bot_instance = TeamSpeakBot(
                        host=SERVER_IP,
                        port=QUERY_PORT,
                        username=QUERY_USER,
                        password=QUERY_PASS,
                        server_id=SERVER_ID,
                        nickname=BOT_NICKNAME
                    )
                    bot_start_time = time.time()
                    bot_status = 'online'
                    bot_instance.monitor()
                except Exception as e:
                    print(f"❌ Restart error: {e}")
                    bot_status = 'offline'
                    bot_instance = None
            
            restart_thread = threading.Thread(target=restart_bot, daemon=True)
            restart_thread.start()
            
            return jsonify({
                'success': True,
                'message': '🔄 Bot is restarting... Please wait 5 seconds.'
            })
            
        except Exception as e:
            bot_status = 'offline'
            return jsonify({
                'success': False,
                'message': f'❌ Error: {str(e)}'
            })

def run_flask():
    """Run Flask web server"""
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Control Panel: http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# ============================================
# CONFIGURATION
# ============================================

# Server Connection
SERVER_IP = "ip.tsww.ir"
QUERY_PORT = 5817
QUERY_USER = "serveradmin"
QUERY_PASS = "yLtpb1gx1FWu"
SERVER_ID = 1
BOT_NICKNAME = "Staff"

# Channel Settings (ID or Exact Name)
CHANNEL_MOVE_ME = 12
CHANNEL_AFK = 13

# Admin/Staff Settings for Notifications
NOTIFY_MODE = "both"
NOTIFY_RANK_IDS = [2]
NOTIFY_NAMES = ["Mahbod"]

# AFK Move Settings
MOVE_ON_MIC_MUTE = False
MOVE_ON_SPEAKER_MUTE = True 
MOVE_ON_MIC_DISABLE = True
MOVE_ON_SPEAKER_DISABLE = True
MOVE_ON_AWAY = True
RETURN_FROM_AFK = True

# Command Settings
CMD_PREFIX = "!"
CMD_MODE = "both"
CMD_RANK_IDS = [2]
CMD_NAMES = ["Mahbod"]

# Individual Command Toggles
CMD_HELP_ENABLED = True
CMD_KICK_ENABLED = True
CMD_BAN_ENABLED = True
CMD_UNBAN_ENABLED = True
CMD_POKE_ENABLED = True
CMD_MOVE_ENABLED = True

# ============================================
# AUTO SERVER GROUP SETTINGS
# ============================================

AUTO_SGROUP_ENABLED = True          # Enable/Disable auto server group
NEW_SVGP = 17                       # Server Group to check (Guest)
NORMAL_SVGP = 16                    # Server Group to give (Member)
AUTO_SGROUP_IGNORE_STAFF = False     # Ignore staff members

# ============================================
# MUTE SETTINGS
# ============================================

MUTE_ENABLED = True
MUTE_SERVER_GROUP_ID = 26        # Mute Microphone
MUTE_SERVER_GROUP_ID2 = 27       # Mute Speaker (optional, set to None to disable)
MUTE_COMMAND_ENABLED = True       # Enable !mute command

# ============================================
# JAIL SETTINGS (Enhanced)
# ============================================

JAIL_COMMAND_ENABLED = True       # Enable !jail command

# ============================================
# ANTI-SPAM SETTINGS
# ============================================

# Anti-Spam Master Switch
ANTI_SPAM_ENABLED = True

# Chat Spam Settings
CHAT_ANTI_SPAM_ENABLED = True
CHAT_SPAM_MAX_MESSAGES = 5
CHAT_SPAM_TIME_WINDOW = 3
CHAT_SPAM_IGNORE_STAFF = True

# Jail Settings (First offense)
JAIL_SERVER_GROUP_ID = 29
JAIL_DURATION = 5
JAIL_AUTO_REMOVE = True

# Ban Settings (Repeat offense)
SPAM_BAN_DURATION = "10m"
SPAM_REPEAT_WINDOW = 300

# Spam Detection Memory Cleanup (seconds)
SPAM_CLEANUP_INTERVAL = 60
JAIL_CHECK_INTERVAL = 30

# ============================================
# ANTI-MOVE SPAM SETTINGS
# ============================================

ANTI_MOVE_SPAM_ENABLED = True
MOVE_SPAM_MAX_MOVES = 5           # Max moves before action
MOVE_SPAM_TIME_WINDOW = 60        # Time window in seconds (1 minute)
MOVE_SPAM_ACTION = "ban"          # "ban", "kick", or "jail"
MOVE_SPAM_ACTION_DURATION = 600   # 10 minutes in seconds
MOVE_SPAM_IGNORE_STAFF = True
MOVE_SPAM_COUNT_AFK = True        # Count AFK moves towards spam detection
MOVE_SPAM_BAN_REASON = "Spam Move"  # Ban reason for move spam

# Monitoring Settings
CHECK_INTERVAL = 2
ADMIN_REFRESH_INTERVAL = 10

# Debug Mode
DEBUG_MODE = False

# ============================================
# BOT CODE
# ============================================

class TeamSpeakBot:
    def __init__(self, host, port, username, password, server_id=1, nickname="Staff"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        
        self.message_queue = deque()
        
        # Anti-Spam tracking
        self.chat_history = defaultdict(list)
        self.spam_offenders = defaultdict(list)
        self.jailed_users = {}  # {clid: (end_time, cldbid)}
        self.muted_users = {}   # {clid: (end_time, sg_list, cldbid)}
        self.last_spam_cleanup = time.time()
        self.last_jail_check = time.time()
        self.last_mute_check = time.time()
        
        # Auto Server Group tracking
        self.sgroup_given = set()
        
        # Anti-Move Spam tracking
        self.move_history = defaultdict(list)  # {clid: [timestamp, ...]}
        self.last_move_cleanup = time.time()
        
        try:
            self.sock.connect((host, port))
            print(f"✅ Connected to {host}:{port}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            raise
        
        self._recv_until_prompt()
        
        response = self._send_command(f"login {username} {password}")
        if "error id=0" not in response:
            print(f"❌ Login failed: {response}")
            raise Exception("Login failed")
        print("✅ Login successful")
        
        response = self._send_command(f"use {server_id}")
        if "error id=0" not in response:
            print(f"❌ Server selection failed: {response}")
            raise Exception("Use failed")
        print(f"✅ Virtual server {server_id} selected")
        
        self._send_command(f"clientupdate client_nickname={self._escape(nickname)}")
        
        self._send_command("servernotifyregister event=server")
        self._send_command("servernotifyregister event=textserver")
        self._send_command("servernotifyregister event=textchannel")
        self._send_command("servernotifyregister event=textprivate")
        
        print(f"✅ Bot '{nickname}' is online")
        print(f"✅ Listening for {CMD_PREFIX}commands in all chats")
        print(f"🔄 Auto Server Group: {'ENABLED' if AUTO_SGROUP_ENABLED else 'DISABLED'} (SGID:{NEW_SVGP} → +SGID:{NORMAL_SVGP})")
        print(f"🛡️  Anti-Spam: {'ENABLED' if ANTI_SPAM_ENABLED else 'DISABLED'}")
        print(f"🔇 Mute: {'ENABLED' if MUTE_ENABLED else 'DISABLED'} (SGID:{MUTE_SERVER_GROUP_ID}, {MUTE_SERVER_GROUP_ID2})")
        print(f"🔒 Jail: {'ENABLED' if JAIL_COMMAND_ENABLED else 'DISABLED'} (SGID:{JAIL_SERVER_GROUP_ID})")
        print(f"🚫 Anti-Move Spam: {'ENABLED' if ANTI_MOVE_SPAM_ENABLED else 'DISABLED'} ({MOVE_SPAM_MAX_MOVES}/{MOVE_SPAM_TIME_WINDOW}s)")
        if ANTI_MOVE_SPAM_ENABLED:
            print(f"   Count AFK moves: {'YES' if MOVE_SPAM_COUNT_AFK else 'NO'}")
            print(f"   Reason: \"{MOVE_SPAM_BAN_REASON}\"")
        
        self.nickname = nickname
        self.channel_cache = {}
        self.server_groups_cache = {}
        self.afk_original_channels = {}
        
        self.move_on_mic_mute = MOVE_ON_MIC_MUTE
        self.move_on_speaker_mute = MOVE_ON_SPEAKER_MUTE
        self.move_on_mic_disable = MOVE_ON_MIC_DISABLE
        self.move_on_speaker_disable = MOVE_ON_SPEAKER_DISABLE
        self.move_on_away = MOVE_ON_AWAY
        self.return_from_afk = RETURN_FROM_AFK
        
        self.cmd_prefix = CMD_PREFIX
        self.bot_clid = self._get_own_clid()
        
    def _escape(self, text):
        return str(text).replace('\\', '\\\\').replace('/', '\\/').replace(' ', '\\s').replace('|', '\\p')
    
    def _unescape(self, text):
        return str(text).replace('\\s', ' ').replace('\\p', '|').replace('\\/', '/').replace('\\\\', '\\')
    
    def _send_raw(self, cmd):
        if DEBUG_MODE:
            print(f"  SEND: {cmd}")
        self.sock.send(f"{cmd}\n".encode('utf-8'))
    
    def _recv_until_prompt(self):
        data = b""
        while True:
            try:
                self.sock.settimeout(0.3)
                chunk = self.sock.recv(8192)
                if not chunk:
                    break
                data += chunk
                
                decoded = data.decode('utf-8', errors='ignore')
                
                if 'notifytextmessage' in decoded:
                    lines = decoded.split('\n')
                    remaining = []
                    for line in lines:
                        if 'notifytextmessage' in line:
                            self._queue_message(line)
                        elif 'error id=' in line:
                            remaining.append(line)
                        else:
                            remaining.append(line)
                    data = '\n'.join(remaining).encode('utf-8')
                
                if b"error id=" in chunk:
                    break
            except socket.timeout:
                break
            except Exception as e:
                if DEBUG_MODE:
                    print(f"  RECV ERROR: {e}")
                break
        
        result = data.decode('utf-8', errors='ignore')
        if DEBUG_MODE and result.strip():
            print(f"  RECV: {result[:200]}")
        return result
    
    def _send_command(self, cmd):
        self._send_raw(cmd)
        return self._recv_until_prompt()
    
    def _queue_message(self, line):
        msg_match = re.search(r'msg=([^\s]+)', line)
        invoker_match = re.search(r'invokerid=(\d+)', line)
        targetmode_match = re.search(r'targetmode=(\d+)', line)
        
        if not msg_match or not invoker_match or not targetmode_match:
            return
        
        message = self._unescape(msg_match.group(1))
        invoker_clid = invoker_match.group(1)
        targetmode = targetmode_match.group(1)
        
        if targetmode == '1':
            chat_type = 'private'
        elif targetmode == '2':
            chat_type = 'channel'
        elif targetmode == '3':
            chat_type = 'server'
        else:
            return
        
        self.message_queue.append({
            'type': chat_type,
            'clid': invoker_clid,
            'message': message
        })
    
    def _process_message_queue(self):
        while self.message_queue:
            msg_data = self.message_queue.popleft()
            
            if msg_data['clid'] == self.bot_clid:
                continue
            
            if ANTI_SPAM_ENABLED and CHAT_ANTI_SPAM_ENABLED:
                if self.check_chat_spam(msg_data['clid'], msg_data['message']):
                    continue
            
            self.handle_command(
                msg_data['clid'],
                msg_data['message'],
                msg_data['type']
            )
    
    def _get_own_clid(self):
        response = self._send_command("whoami")
        match = re.search(r'clid=(\d+)', response)
        return match.group(1) if match else None
    
    # ============================================
    # AUTO SERVER GROUP
    # ============================================
    
    def _get_client_server_groups(self, clid):
        """Get list of server group IDs for a client"""
        info = self.get_client_detailed_info(clid)
        groups_str = info.get('client_servergroups', '')
        if groups_str:
            return groups_str.split(',')
        return []
    
    def _give_normal_sgroup(self, clid, name):
        """Give NORMAL_SVGP to user if they have NEW_SVGP"""
        if not AUTO_SGROUP_ENABLED:
            return False
        
        if clid in self.sgroup_given:
            return False
        
        if AUTO_SGROUP_IGNORE_STAFF and self._is_staff(clid):
            self.sgroup_given.add(clid)
            return False
        
        cldbid = self._get_client_database_id(clid)
        if not cldbid:
            return False
        
        # Check if user has NEW_SVGP (Guest)
        client_groups = self._get_client_server_groups(clid)
        
        if str(NEW_SVGP) in client_groups:
            # Give NORMAL_SVGP (Member)
            if self._add_server_group(cldbid, str(NORMAL_SVGP)):
                print(f"   🔄 Auto SG: {name} (SGID:{NEW_SVGP}) → +SGID:{NORMAL_SVGP}")
                self.send_poke(clid, f"Welcome {name}! You have been promoted to Member.")
                self.sgroup_given.add(clid)
                return True
        
        # Mark as checked anyway
        self.sgroup_given.add(clid)
        return False
    
    # ============================================
    # MUTE METHODS
    # ============================================
    
    def _mute_user(self, clid, name, duration_minutes, cldbid=None):
        """Mute a user by adding server groups for specified duration"""
        if not cldbid:
            cldbid = self._get_client_database_id(clid)
        if not cldbid:
            return False
        
        sg_list = []
        success = True
        
        # Add first mute group
        if self._add_server_group(cldbid, str(MUTE_SERVER_GROUP_ID)):
            sg_list.append(MUTE_SERVER_GROUP_ID)
            print(f"   🔇 Added mute SGID:{MUTE_SERVER_GROUP_ID} to {name}")
        else:
            success = False
        
        # Add second mute group if configured
        if MUTE_SERVER_GROUP_ID2:
            if self._add_server_group(cldbid, str(MUTE_SERVER_GROUP_ID2)):
                sg_list.append(MUTE_SERVER_GROUP_ID2)
                print(f"   🔇 Added mute SGID:{MUTE_SERVER_GROUP_ID2} to {name}")
            else:
                success = False
        
        if sg_list:
            if duration_minutes > 0:
                mute_end = time.time() + (duration_minutes * 60)
                self.muted_users[clid] = (mute_end, sg_list, cldbid)
                time_display = self._format_time_display(duration_minutes)
                print(f"   🔇 Muted {name} for {time_display}")
                self.send_poke(clid, f"🔇 You have been muted for {time_display}")
            else:
                # Permanent mute
                self.muted_users[clid] = (float('inf'), sg_list, cldbid)
                print(f"   🔇 Muted {name} permanently")
                self.send_poke(clid, "🔇 You have been permanently muted")
        
        return success
    
    def _unmute_user(self, clid, name, cldbid=None):
        """Remove mute server groups"""
        if clid not in self.muted_users:
            return False
        
        if not cldbid:
            cldbid = self._get_client_database_id(clid)
        if not cldbid:
            # Try to get from stored data
            _, _, cldbid = self.muted_users[clid]
        
        _, sg_list, _ = self.muted_users[clid]
        
        success = True
        for sgid in sg_list:
            if not self._remove_server_group(cldbid, str(sgid)):
                success = False
        
        del self.muted_users[clid]
        print(f"   🔈 Unmuted {name}")
        self.send_poke(clid, "🔈 You have been unmuted")
        
        return success
    
    def _check_muted_users(self):
        """Check and remove expired mutes"""
        current_time = time.time()
        
        for clid in list(self.muted_users.keys()):
            end_time, sg_list, cldbid = self.muted_users[clid]
            
            if current_time >= end_time and end_time != float('inf'):
                name = self.get_client_nickname(clid)
                success = True
                for sgid in sg_list:
                    if not self._remove_server_group(cldbid, str(sgid)):
                        success = False
                
                if success:
                    print(f"   🔈 Auto-unmuted {name}")
                    self.send_poke(clid, "🔈 Your mute has expired")
                del self.muted_users[clid]
    
    # ============================================
    # JAIL METHODS (Enhanced)
    # ============================================
    
    def _jail_user_cmd(self, clid, name, duration_minutes, cldbid=None):
        """Jail a user via command for specified duration"""
        if not cldbid:
            cldbid = self._get_client_database_id(clid)
        if not cldbid:
            return False
        
        if self._add_server_group(cldbid, str(JAIL_SERVER_GROUP_ID)):
            if duration_minutes > 0:
                jail_end = time.time() + (duration_minutes * 60)
                self.jailed_users[clid] = (jail_end, cldbid)
                time_display = self._format_time_display(duration_minutes)
                print(f"   🔒 Jailed {name} for {time_display}")
                self.send_poke(clid, f"🔒 You have been jailed for {time_display}")
            else:
                # Permanent jail
                self.jailed_users[clid] = (float('inf'), cldbid)
                print(f"   🔒 Jailed {name} permanently")
                self.send_poke(clid, "🔒 You have been permanently jailed")
            return True
        return False
    
    def _remove_jail(self, clid):
        """Remove jail server group"""
        if clid not in self.jailed_users:
            return
        
        _, cldbid = self.jailed_users[clid]
        
        if self._remove_server_group(cldbid, str(JAIL_SERVER_GROUP_ID)):
            name = self.get_client_nickname(clid)
            print(f"   🔓 Unjailed {name}")
            self.send_poke(clid, "🔓 You have been released from jail")
        
        del self.jailed_users[clid]
    
    def _check_jailed_users(self):
        """Check and remove expired jails"""
        if not JAIL_AUTO_REMOVE:
            return
        
        current_time = time.time()
        
        for clid in list(self.jailed_users.keys()):
            end_time, cldbid = self.jailed_users[clid]
            
            if current_time >= end_time and end_time != float('inf'):
                if self._remove_server_group(cldbid, str(JAIL_SERVER_GROUP_ID)):
                    name = self.get_client_nickname(clid)
                    print(f"   🔓 Auto-released {name} from jail")
                    self.send_poke(clid, "🔓 Your jail time has expired")
                del self.jailed_users[clid]
    
    # ============================================
    # ANTI-MOVE SPAM METHODS
    # ============================================
    
    def _track_move(self, clid, move_type="manual"):
        """Track a move for spam detection
        
        Args:
            clid: Client ID that was moved
            move_type: Type of move - "manual" (by command), "afk" (by AFK detection), "return" (return from AFK)
        """
        if not ANTI_MOVE_SPAM_ENABLED:
            return False
        
        if MOVE_SPAM_IGNORE_STAFF and self._is_staff(clid):
            return False
        
        # Don't count AFK moves if disabled
        if move_type in ["afk", "return"] and not MOVE_SPAM_COUNT_AFK:
            return False
        
        current_time = time.time()
        self.move_history[clid].append({
            'timestamp': current_time,
            'type': move_type
        })
        
        # Check for spam
        return self._check_move_spam(clid)
    
    def _check_move_spam(self, clid):
        """Check if a user has been moved too frequently"""
        if not ANTI_MOVE_SPAM_ENABLED:
            return False
        
        if MOVE_SPAM_IGNORE_STAFF and self._is_staff(clid):
            return False
        
        current_time = time.time()
        
        # Clean old entries
        window_start = current_time - MOVE_SPAM_TIME_WINDOW
        self.move_history[clid] = [m for m in self.move_history[clid] if m['timestamp'] >= window_start]
        
        if len(self.move_history[clid]) >= MOVE_SPAM_MAX_MOVES:
            name = self.get_client_nickname(clid)
            
            # Count move types
            manual_count = sum(1 for m in self.move_history[clid] if m['type'] == 'manual')
            afk_count = sum(1 for m in self.move_history[clid] if m['type'] == 'afk')
            return_count = sum(1 for m in self.move_history[clid] if m['type'] == 'return')
            
            move_details = []
            if manual_count > 0:
                move_details.append(f"{manual_count} manual")
            if afk_count > 0:
                move_details.append(f"{afk_count} AFK")
            if return_count > 0:
                move_details.append(f"{return_count} return")
            
            move_detail_str = ", ".join(move_details)
            
            print(f"🚫 MOVE SPAM: {name} ({len(self.move_history[clid])} moves: {move_detail_str} in {MOVE_SPAM_TIME_WINDOW}s)")
            
            if MOVE_SPAM_ACTION == "ban":
                print(f"   🔨 Banning for {MOVE_SPAM_ACTION_DURATION}s - Reason: {MOVE_SPAM_BAN_REASON}")
                self.ban_client(clid, MOVE_SPAM_ACTION_DURATION, MOVE_SPAM_BAN_REASON)
                self.send_poke(clid, f"🚫 Banned for move spam ({MOVE_SPAM_BAN_REASON})")
            elif MOVE_SPAM_ACTION == "kick":
                print(f"   👢 Kicking - Reason: {MOVE_SPAM_BAN_REASON}")
                self.kick_client(clid, MOVE_SPAM_BAN_REASON)
            elif MOVE_SPAM_ACTION == "jail":
                jail_duration = MOVE_SPAM_ACTION_DURATION // 60  # Convert to minutes
                print(f"   🔒 Jailing for {jail_duration}min")
                cldbid = self._get_client_database_id(clid)
                if cldbid:
                    self._jail_user_cmd(clid, name, jail_duration, cldbid)
            
            # Clear history after action
            self.move_history[clid] = []
            return True
        
        return False
    
    def _cleanup_move_history(self):
        """Clean up old move history entries"""
        current_time = time.time()
        
        for clid in list(self.move_history.keys()):
            self.move_history[clid] = [m for m in self.move_history[clid] if current_time - m['timestamp'] < MOVE_SPAM_TIME_WINDOW * 2]
            if not self.move_history[clid]:
                del self.move_history[clid]
    
    # ============================================
    # ANTI-SPAM
    # ============================================
    
    def _cleanup_spam_history(self):
        current_time = time.time()
        
        for clid in list(self.chat_history.keys()):
            self.chat_history[clid] = [t for t in self.chat_history[clid] if current_time - t < 120]
            if not self.chat_history[clid]:
                del self.chat_history[clid]
        
        for clid in list(self.spam_offenders.keys()):
            self.spam_offenders[clid] = [t for t in self.spam_offenders[clid] if current_time - t < SPAM_REPEAT_WINDOW]
            if not self.spam_offenders[clid]:
                del self.spam_offenders[clid]
    
    def _add_server_group(self, cldbid, sgid):
        response = self._send_command(f"servergroupaddclient sgid={sgid} cldbid={cldbid}")
        return "error id=0" in response
    
    def _remove_server_group(self, cldbid, sgid):
        response = self._send_command(f"servergroupdelclient sgid={sgid} cldbid={cldbid}")
        return "error id=0" in response
    
    def _get_client_database_id(self, clid):
        info = self.get_client_detailed_info(clid)
        return info.get('client_database_id')
    
    def _is_staff(self, clid):
        if CMD_MODE == "all":
            return True
        
        if CMD_MODE in ["rank", "both"]:
            rank_targets = self.get_clients_by_ranks(CMD_RANK_IDS)
            if clid in rank_targets:
                return True
        
        if CMD_MODE in ["name", "both"]:
            name_targets = self.get_clients_by_names(CMD_NAMES)
            if clid in name_targets:
                return True
        
        return False
    
    def check_chat_spam(self, clid, message):
        if not ANTI_SPAM_ENABLED or not CHAT_ANTI_SPAM_ENABLED:
            return False
        
        if CHAT_SPAM_IGNORE_STAFF and self._is_staff(clid):
            return False
        
        if message.startswith(self.cmd_prefix):
            return False
        
        if clid in self.jailed_users:
            return False
        
        current_time = time.time()
        self.chat_history[clid].append(current_time)
        
        window_start = current_time - CHAT_SPAM_TIME_WINDOW
        self.chat_history[clid] = [t for t in self.chat_history[clid] if t >= window_start]
        
        if len(self.chat_history[clid]) >= CHAT_SPAM_MAX_MESSAGES:
            name = self.get_client_nickname(clid)
            print(f"🛡️ SPAM: {name}")
            
            self.spam_offenders[clid].append(current_time)
            offense_count = len([t for t in self.spam_offenders[clid] if current_time - t < SPAM_REPEAT_WINDOW])
            
            if offense_count >= 2:
                self._handle_repeat_spam(clid, name)
            else:
                self._handle_first_spam(clid, name)
            
            self.chat_history[clid] = []
            return True
        
        return False
    
    def _handle_first_spam(self, clid, name):
        print(f"   ⚠️ First offense → Jail {JAIL_DURATION}min")
        cldbid = self._get_client_database_id(clid)
        if cldbid:
            self._jail_user_cmd(clid, name, JAIL_DURATION, cldbid)
    
    def _handle_repeat_spam(self, clid, name):
        print(f"   🚨 Repeat → Ban {SPAM_BAN_DURATION}")
        time_seconds = self.parse_time_string(SPAM_BAN_DURATION)
        self.ban_client(clid, time_seconds, "Anti-Spam: Repeat offender")
        self.spam_offenders[clid] = []
        if clid in self.jailed_users:
            del self.jailed_users[clid]
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def resolve_channel_id(self, channel_input):
        if channel_input is None:
            return None
        
        channel_input = str(channel_input)
        
        if channel_input.isdigit():
            return channel_input
        
        if not self.channel_cache:
            self.get_channel_list()
        
        for name, cid in self.channel_cache.items():
            if name.lower() == channel_input.lower():
                return cid
        
        for name, cid in self.channel_cache.items():
            if channel_input.lower() in name.lower():
                return cid
        
        return None
    
    def get_channel_list(self):
        response = self._send_command("channellist")
        
        channels = {}
        for match in re.finditer(r'cid=(\d+).*?channel_name=([^|]+?)(?:\s+\w+=|$)', response):
            cid = match.group(1)
            name = self._unescape(match.group(2).strip())
            channels[name] = cid
        
        self.channel_cache = channels
        return channels
    
    def get_channel_name(self, cid):
        if not self.channel_cache:
            self.get_channel_list()
        for name, channel_id in self.channel_cache.items():
            if channel_id == str(cid):
                return name
        return f"Channel_{cid}"
    
    def get_server_groups(self):
        response = self._send_command("servergrouplist")
        
        groups = {}
        for match in re.finditer(r'sgid=(\d+).*?name=([^\s|]+)', response):
            sgid = match.group(1)
            name = self._unescape(match.group(2))
            groups[sgid] = name
        
        self.server_groups_cache = groups
        return groups
    
    def get_client_list_raw(self):
        response = self._send_command("clientlist -uid -groups -voice -info -country")
        
        clients = []
        entries = response.split('|')
        current_client = {}
        
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            
            if 'clid=' in entry and current_client:
                clients.append(current_client)
                current_client = {}
            
            for match in re.finditer(r'(\w+)=([^\s|]+)', entry):
                key = match.group(1)
                value = self._unescape(match.group(2))
                current_client[key] = value
        
        if current_client:
            clients.append(current_client)
        
        return clients
    
    def get_client_detailed_info(self, clid):
        response = self._send_command(f"clientinfo clid={clid}")
        
        info = {}
        for match in re.finditer(r'(\w+)=([^\s|]+)', response):
            key = match.group(1)
            value = self._unescape(match.group(2))
            info[key] = value
        
        return info
    
    def get_client_nickname(self, clid):
        info = self.get_client_detailed_info(clid)
        return info.get('client_nickname', f'User_{clid}')
    
    def get_client_channel(self, clid):
        info = self.get_client_detailed_info(clid)
        return info.get('cid')
    
    def find_client_by_name(self, name):
        clients = self.get_client_list_raw()
        
        for c in clients:
            if c.get('client_type') == '0':
                clid = c.get('clid')
                nickname = self.get_client_nickname(clid)
                if nickname.lower() == name.lower():
                    return clid
        
        for c in clients:
            if c.get('client_type') == '0':
                clid = c.get('clid')
                nickname = self.get_client_nickname(clid)
                if name.lower() in nickname.lower():
                    return clid
        
        return None
    
    def get_clients_by_ranks(self, rank_ids):
        response = self._send_command("clientlist -groups")
        
        targets = {}
        entries = response.split('|')
        current_clid = None
        current_groups = ""
        current_nickname = ""
        
        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue
            
            if 'clid=' in entry:
                if current_clid:
                    client_groups = current_groups.split(',') if current_groups else []
                    for rid in rank_ids:
                        if str(rid) in client_groups:
                            targets[current_clid] = current_nickname
                            break
                
                clid_match = re.search(r'clid=(\d+)', entry)
                if clid_match:
                    current_clid = clid_match.group(1)
                current_groups = ""
                current_nickname = ""
            
            if 'client_servergroups=' in entry:
                groups_match = re.search(r'client_servergroups=([\d,]+)', entry)
                if groups_match:
                    current_groups = groups_match.group(1)
            
            if 'client_nickname=' in entry:
                name_match = re.search(r'client_nickname=([^\s|]+)', entry)
                if name_match:
                    current_nickname = self._unescape(name_match.group(1))
        
        if current_clid:
            client_groups = current_groups.split(',') if current_groups else []
            for rid in rank_ids:
                if str(rid) in client_groups:
                    targets[current_clid] = current_nickname
                    break
        
        return targets
    
    def get_clients_by_names(self, names):
        clients = self.get_client_list_raw()
        targets = {}
        
        for c in clients:
            if c.get('client_type') == '0':
                clid = c.get('clid')
                nickname = self.get_client_nickname(clid)
                
                for name in names:
                    if name.lower() in nickname.lower():
                        targets[clid] = nickname
                        break
        
        return targets
    
    def get_notify_targets(self):
        targets = {}
        
        if NOTIFY_MODE in ["rank", "both"] and NOTIFY_RANK_IDS:
            targets.update(self.get_clients_by_ranks(NOTIFY_RANK_IDS))
        
        if NOTIFY_MODE in ["name", "both"] and NOTIFY_NAMES:
            targets.update(self.get_clients_by_names(NOTIFY_NAMES))
        
        return targets
    
    def can_use_commands(self, clid):
        return self._is_staff(clid)
    
    def send_poke(self, clid, message):
        msg_escaped = self._escape(message)
        response = self._send_command(f"clientpoke clid={clid} msg={msg_escaped}")
        return "error id=0" in response
    
    def send_private_message(self, clid, message):
        msg_escaped = self._escape(message)
        response = self._send_command(f"sendtextmessage targetmode=1 target={clid} msg={msg_escaped}")
        return "error id=0" in response
    
    def send_channel_message(self, message):
        msg_escaped = self._escape(message)
        response = self._send_command(f"sendtextmessage targetmode=2 msg={msg_escaped}")
        return "error id=0" in response
    
    def move_client(self, clid, cid):
        response = self._send_command(f"clientmove clid={clid} cid={cid}")
        return "error id=0" in response
    
    def kick_client(self, clid, reason="Kicked by bot"):
        reason_escaped = self._escape(reason)
        response = self._send_command(f"clientkick clid={clid} reasonid=5 reasonmsg={reason_escaped}")
        return "error id=0" in response
    
    def ban_client(self, clid, time_seconds=0, reason="Banned by bot"):
        reason_escaped = self._escape(reason)
        response = self._send_command(f"banclient clid={clid} time={time_seconds} banreason={reason_escaped}")
        
        if "error id=0" in response:
            banid_match = re.search(r'banid=(\d+)', response)
            return banid_match.group(1) if banid_match else True
        return False
    
    def unban_client(self, banid):
        response = self._send_command(f"bandel banid={banid}")
        return "error id=0" in response
    
    def find_ban_by_name(self, name):
        response = self._send_command("banlist")
        
        for match in re.finditer(r'banid=(\d+).*?name=([^\s|]+)', response):
            banid = match.group(1)
            banned_name = self._unescape(match.group(2))
            if name.lower() in banned_name.lower():
                return banid
        
        return None
    
    def parse_time_string(self, time_str):
        """Parse time string like 10m, 1h, 2d, 1w, 3mo, 1y, l/life"""
        if not time_str or time_str.lower() in ['l', 'life']:
            return 0  # 0 means permanent/life
        
        match = re.match(r'(\d+)(mo|[smhdwy]|l)', time_str.lower())
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800,
            'mo': 2592000,  # 30 days
            'y': 31536000,
            'l': 0
        }
        
        return value * multipliers.get(unit, 0)
    
    def _format_time_display(self, total_minutes):
        """Format minutes into human readable string"""
        if total_minutes < 60:
            return f"{total_minutes} minute(s)"
        elif total_minutes < 1440:
            hours = total_minutes // 60
            mins = total_minutes % 60
            if mins > 0:
                return f"{hours}h {mins}m"
            return f"{hours} hour(s)"
        elif total_minutes < 43200:  # 30 days
            days = total_minutes // 1440
            hours = (total_minutes % 1440) // 60
            if hours > 0:
                return f"{days}d {hours}h"
            return f"{days} day(s)"
        else:
            months = total_minutes // 43200
            days = (total_minutes % 43200) // 1440
            if days > 0:
                return f"{months}mo {days}d"
            return f"{months} month(s)"
    
    # ============================================
    # COMMANDS
    # ============================================
    
    def handle_command(self, invoker_clid, message, chat_type='channel'):
        message = message.strip()
        
        if not message.startswith(self.cmd_prefix):
            return
        
        if not self.can_use_commands(invoker_clid):
            self.reply_to_command(invoker_clid, chat_type, "❌ You don't have permission!")
            return
        
        cmd_text = message[len(self.cmd_prefix):].strip()
        parts = cmd_text.split()
        if not parts:
            return
        
        command = parts[0].lower()
        
        if command == 'help' and CMD_HELP_ENABLED:
            self.cmd_help(invoker_clid)
            if chat_type != 'private':
                self.reply_to_command(invoker_clid, chat_type, "📨 Commands sent to private chat!")
            return
        
        elif command == 'kick' and CMD_KICK_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            reason = ' '.join(parts[2:]) if len(parts) > 2 else "Kicked by Staff"
            self.cmd_kick(invoker_clid, target, reason, chat_type)
        
        elif command == 'ban' and CMD_BAN_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            time_str = parts[2] if len(parts) > 2 else 'life'
            reason = ' '.join(parts[3:]) if len(parts) > 3 else "Banned by Staff"
            self.cmd_ban(invoker_clid, target, time_str, reason, chat_type)
        
        elif command == 'unban' and CMD_UNBAN_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            self.cmd_unban(invoker_clid, target, chat_type)
        
        elif command == 'poke' and CMD_POKE_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            msg = ' '.join(parts[2:]) if len(parts) > 2 else "Poke from Staff"
            self.cmd_poke(invoker_clid, target, msg, chat_type)
        
        elif command == 'move' and CMD_MOVE_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            channel = ' '.join(parts[2:]) if len(parts) > 2 else None
            self.cmd_move(invoker_clid, target, channel, chat_type)
        
        elif command == 'mute' and MUTE_COMMAND_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            time_str = parts[2] if len(parts) > 2 else 'life'
            self.cmd_mute(invoker_clid, target, time_str, chat_type)
        
        elif command == 'unmute' and MUTE_COMMAND_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            self.cmd_unmute(invoker_clid, target, chat_type)
        
        elif command == 'jail' and JAIL_COMMAND_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            time_str = parts[2] if len(parts) > 2 else 'life'
            self.cmd_jail(invoker_clid, target, time_str, chat_type)
        
        elif command == 'unjail' and JAIL_COMMAND_ENABLED:
            target = parts[1] if len(parts) > 1 else None
            self.cmd_unjail(invoker_clid, target, chat_type)
    
    def reply_to_command(self, invoker_clid, chat_type, message):
        if chat_type == 'private':
            self.send_private_message(invoker_clid, message)
        elif chat_type == 'channel':
            self.send_channel_message(message)
        elif chat_type == 'server':
            self.send_private_message(invoker_clid, message)
    
    def cmd_help(self, invoker_clid):
        """Enhanced help with new commands"""
        help_parts = [f"CMD's ({CMD_PREFIX}):"]
        
        if CMD_POKE_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Poke [Name] [Message]")
        if CMD_MOVE_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Move [Name] [Channel/Me]")
        if CMD_KICK_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Kick [Name] [Reason]")
        if CMD_BAN_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Ban [Name] [Time] [Reason]")
        if CMD_UNBAN_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Unban [Name]")
        if MUTE_COMMAND_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Mute [Name] [Time]")
            help_parts.append(f"  {CMD_PREFIX}Unmute [Name]")
        if JAIL_COMMAND_ENABLED:
            help_parts.append(f"  {CMD_PREFIX}Jail [Name] [Time]")
            help_parts.append(f"  {CMD_PREFIX}Unjail [Name]")
        
        help_parts.append(f"\n⏱ Time: s,m,h,d,w,mo,y,life")
        
        help_msg = "\n".join(help_parts)
        self.send_private_message(invoker_clid, help_msg)
        print(f"📨 Help sent to {self.get_client_nickname(invoker_clid)}")
    
    def cmd_kick(self, invoker_clid, target_name, reason, chat_type='channel'):
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Kick [Name]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        nickname = self.get_client_nickname(target_clid)
        
        if self.kick_client(target_clid, reason):
            self.reply_to_command(invoker_clid, chat_type, f"✅ Kicked '{nickname}'")
            print(f"👢 {self.get_client_nickname(invoker_clid)} kicked {nickname}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to kick '{nickname}'")
    
    def cmd_ban(self, invoker_clid, target_name, time_str, reason, chat_type='channel'):
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Ban [Name] [Time]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        time_seconds = self.parse_time_string(time_str)
        if time_seconds is None:
            self.reply_to_command(invoker_clid, chat_type, "❌ Invalid time! Use: 1s,2m,3h,4d,5w,1mo,1y,life")
            return
        
        nickname = self.get_client_nickname(target_clid)
        
        result = self.ban_client(target_clid, time_seconds, reason)
        if result:
            time_display = time_str.upper() if time_str.lower() not in ['l', 'life'] else 'PERMANENT'
            self.reply_to_command(invoker_clid, chat_type, f"✅ Banned '{nickname}' | {time_display}")
            print(f"🔨 {self.get_client_nickname(invoker_clid)} banned {nickname} ({time_display})")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to ban '{nickname}'")
    
    def cmd_unban(self, invoker_clid, target_name, chat_type='channel'):
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Unban [Name]")
            return
        
        banid = self.find_ban_by_name(target_name)
        if not banid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ No ban found for '{target_name}'")
            return
        
        if self.unban_client(banid):
            self.reply_to_command(invoker_clid, chat_type, f"✅ Unbanned '{target_name}'")
            print(f"🔓 {self.get_client_nickname(invoker_clid)} unbanned {target_name}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to unban '{target_name}'")
    
    def cmd_poke(self, invoker_clid, target_name, message, chat_type='channel'):
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Poke [Name] [Message]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        nickname = self.get_client_nickname(target_clid)
        
        if self.send_poke(target_clid, message):
            self.reply_to_command(invoker_clid, chat_type, f"✅ Poked '{nickname}'")
            print(f"📨 {self.get_client_nickname(invoker_clid)} poked {nickname}: {message}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to poke '{nickname}'")
    
    def cmd_move(self, invoker_clid, target_name, channel_input, chat_type='channel'):
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Move [Name] [Channel/Me]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        # Track this move for spam detection (before actually moving)
        if self._track_move(target_clid, "manual"):
            # _track_move returns True if spam detected and action taken
            self.reply_to_command(invoker_clid, chat_type, f"⚠️ '{target_name}' has been moved too frequently ({MOVE_SPAM_BAN_REASON})!")
            return
        
        if channel_input and channel_input.lower() == 'me':
            invoker_channel = self.get_client_channel(invoker_clid)
            if not invoker_channel:
                self.reply_to_command(invoker_clid, chat_type, "❌ Could not find your channel!")
                return
            
            channel_id = invoker_channel
            channel_name = self.get_channel_name(channel_id)
        else:
            if not channel_input:
                self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Move [Name] [Channel/Me]")
                return
            
            channel_id = self.resolve_channel_id(channel_input)
            if not channel_id:
                self.reply_to_command(invoker_clid, chat_type, f"❌ Channel '{channel_input}' not found!")
                return
            
            channel_name = self.get_channel_name(channel_id)
        
        nickname = self.get_client_nickname(target_clid)
        invoker_name = self.get_client_nickname(invoker_clid)
        
        if self.move_client(target_clid, channel_id):
            if channel_input and channel_input.lower() == 'me':
                self.reply_to_command(invoker_clid, chat_type, f"✅ Moved '{nickname}' to your channel")
            else:
                self.reply_to_command(invoker_clid, chat_type, f"✅ Moved '{nickname}' → {channel_name}")
            print(f"🔄 {invoker_name} moved {nickname} → {channel_name}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to move '{nickname}'")
    
    def cmd_mute(self, invoker_clid, target_name, time_str, chat_type='channel'):
        """!mute [name] [time]"""
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Mute [Name] [Time]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        time_seconds = self.parse_time_string(time_str)
        if time_seconds is None:
            self.reply_to_command(invoker_clid, chat_type, "❌ Invalid time! Use: 1s,2m,3h,4d,5w,1mo,1y,life")
            return
        
        nickname = self.get_client_nickname(target_clid)
        cldbid = self._get_client_database_id(target_clid)
        
        # Convert seconds to minutes for storage
        if time_seconds == 0:
            duration_minutes = 0  # Permanent
        else:
            duration_minutes = time_seconds // 60
            if duration_minutes < 1:
                duration_minutes = 1  # Minimum 1 minute
        
        if self._mute_user(target_clid, nickname, duration_minutes, cldbid):
            time_display = time_str.upper() if time_str.lower() not in ['l', 'life'] else 'PERMANENT'
            self.reply_to_command(invoker_clid, chat_type, f"✅ Muted '{nickname}' | {time_display}")
            print(f"🔇 {self.get_client_nickname(invoker_clid)} muted {nickname} ({time_display})")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to mute '{nickname}'")
    
    def cmd_unmute(self, invoker_clid, target_name, chat_type='channel'):
        """!unmute [name]"""
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Unmute [Name]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        if target_clid not in self.muted_users:
            self.reply_to_command(invoker_clid, chat_type, f"❌ '{target_name}' is not muted!")
            return
        
        nickname = self.get_client_nickname(target_clid)
        
        if self._unmute_user(target_clid, nickname):
            self.reply_to_command(invoker_clid, chat_type, f"✅ Unmuted '{nickname}'")
            print(f"🔈 {self.get_client_nickname(invoker_clid)} unmuted {nickname}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to unmute '{nickname}'")
    
    def cmd_jail(self, invoker_clid, target_name, time_str, chat_type='channel'):
        """!jail [name] [time]"""
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Jail [Name] [Time]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        time_seconds = self.parse_time_string(time_str)
        if time_seconds is None:
            self.reply_to_command(invoker_clid, chat_type, "❌ Invalid time! Use: 1s,2m,3h,4d,5w,1mo,1y,life")
            return
        
        nickname = self.get_client_nickname(target_clid)
        cldbid = self._get_client_database_id(target_clid)
        
        # Convert seconds to minutes for storage
        if time_seconds == 0:
            duration_minutes = 0  # Permanent
        else:
            duration_minutes = time_seconds // 60
            if duration_minutes < 1:
                duration_minutes = 1  # Minimum 1 minute
        
        if self._jail_user_cmd(target_clid, nickname, duration_minutes, cldbid):
            time_display = time_str.upper() if time_str.lower() not in ['l', 'life'] else 'PERMANENT'
            self.reply_to_command(invoker_clid, chat_type, f"✅ Jailed '{nickname}' | {time_display}")
            print(f"🔒 {self.get_client_nickname(invoker_clid)} jailed {nickname} ({time_display})")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to jail '{nickname}'")
    
    def cmd_unjail(self, invoker_clid, target_name, chat_type='channel'):
        """!unjail [name]"""
        if not target_name:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Usage: {CMD_PREFIX}Unjail [Name]")
            return
        
        target_clid = self.find_client_by_name(target_name)
        if not target_clid:
            self.reply_to_command(invoker_clid, chat_type, f"❌ User '{target_name}' not found!")
            return
        
        if target_clid not in self.jailed_users:
            self.reply_to_command(invoker_clid, chat_type, f"❌ '{target_name}' is not jailed!")
            return
        
        nickname = self.get_client_nickname(target_clid)
        
        if self._remove_jail(target_clid):
            self.reply_to_command(invoker_clid, chat_type, f"✅ Unjailed '{nickname}'")
            print(f"🔓 {self.get_client_nickname(invoker_clid)} unjailed {nickname}")
        else:
            self.reply_to_command(invoker_clid, chat_type, f"❌ Failed to unjail '{nickname}'")
    
    def check_afk_state(self, clid):
        info = self.get_client_detailed_info(clid)
        reasons = []
        
        if self.move_on_mic_mute:
            if info.get('client_input_muted', '0') == '1':
                reasons.append("Mic Muted")
        
        if self.move_on_speaker_mute:
            if info.get('client_output_muted', '0') == '1':
                reasons.append("Speaker Muted")
        
        if self.move_on_mic_disable:
            if info.get('client_input_hardware', '1') == '0':
                reasons.append("Mic Disabled")
        
        if self.move_on_speaker_disable:
            if info.get('client_output_hardware', '1') == '0':
                reasons.append("Speaker Disabled")
        
        if self.move_on_away:
            if info.get('client_away', '0') == '1':
                reasons.append("Away")
        
        return len(reasons) > 0, reasons
    
    def monitor(self):
        print("\n" + "=" * 60)
        print("🔍 STARTING MONITORING...")
        print("=" * 60)
        
        move_me_cid = self.resolve_channel_id(CHANNEL_MOVE_ME)
        afk_cid = self.resolve_channel_id(CHANNEL_AFK) if CHANNEL_AFK else None
        
        if not move_me_cid:
            print("❌ Move Me channel not found!")
            return
        
        print(f"\n⚙️  Configuration:")
        print(f"   📌 Move Me: {self.get_channel_name(move_me_cid)} (CID: {move_me_cid})")
        if afk_cid:
            print(f"   💤 AFK: {self.get_channel_name(afk_cid)} (CID: {afk_cid})")
        print(f"   ⌨️  Prefix: \"{CMD_PREFIX}\" | 💬 All chats")
        print(f"   🔄 Auto SG: SGID:{NEW_SVGP} → +SGID:{NORMAL_SVGP}")
        
        print(f"\n🛡️  Anti-Spam: {'ENABLED' if ANTI_SPAM_ENABLED else 'DISABLED'}")
        if ANTI_SPAM_ENABLED:
            print(f"   🔒 1st: Jail {JAIL_DURATION}min → 🔨 Repeat: Ban {SPAM_BAN_DURATION}")
        
        print(f"\n🚫 Anti-Move Spam: {'ENABLED' if ANTI_MOVE_SPAM_ENABLED else 'DISABLED'}")
        if ANTI_MOVE_SPAM_ENABLED:
            print(f"   Limit: {MOVE_SPAM_MAX_MOVES} moves/{MOVE_SPAM_TIME_WINDOW}s → {MOVE_SPAM_ACTION} {MOVE_SPAM_ACTION_DURATION}s")
            print(f"   Count AFK moves: {'YES' if MOVE_SPAM_COUNT_AFK else 'NO'}")
            print(f"   Ban Reason: \"{MOVE_SPAM_BAN_REASON}\"")
        
        notify_targets = self.get_notify_targets()
        print(f"\n👑 Staff online: {len(notify_targets)}")
        
        old_users = {}
        clients = self.get_client_list_raw()
        for c in clients:
            if c.get('client_type') == '0':
                clid = c.get('clid')
                if clid == self.bot_clid:
                    continue
                
                cid = self.get_client_channel(clid)
                if clid and cid:
                    name = self.get_client_nickname(clid)
                    is_afk, reasons = self.check_afk_state(clid)
                    
                    # Mark existing users as already processed
                    self.sgroup_given.add(clid)
                    
                    old_users[clid] = {
                        'cid': cid,
                        'original_cid': cid,
                        'afk': is_afk
                    }
                    
                    if is_afk:
                        self.afk_original_channels[clid] = cid
                    
                    status = " | ".join(reasons) if reasons else "✅"
                    print(f"   {name} → {self.get_channel_name(cid)} [{status}]")
        
        print(f"\n🟢 Bot running! Type {CMD_PREFIX}Help for commands\n")
        
        last_admin_check = time.time()
        
        while True:
            try:
                self._process_message_queue()
                self._recv_until_prompt()
                self._process_message_queue()
                
                current_time = time.time()
                
                # Regular cleanup
                if current_time - self.last_spam_cleanup > SPAM_CLEANUP_INTERVAL:
                    self._cleanup_spam_history()
                    self.last_spam_cleanup = current_time
                
                if current_time - self.last_jail_check > JAIL_CHECK_INTERVAL:
                    self._check_jailed_users()
                    self.last_jail_check = current_time
                
                if current_time - self.last_mute_check > JAIL_CHECK_INTERVAL:
                    self._check_muted_users()
                    self.last_mute_check = current_time
                
                # Move history cleanup
                if current_time - self.last_move_cleanup > 120:
                    self._cleanup_move_history()
                    self.last_move_cleanup = current_time
                
                if current_time - last_admin_check > ADMIN_REFRESH_INTERVAL:
                    notify_targets = self.get_notify_targets()
                    last_admin_check = current_time
                
                clients = self.get_client_list_raw()
                current_users = {}
                
                for c in clients:
                    if c.get('client_type') == '0':
                        clid = c.get('clid')
                        if clid == self.bot_clid:
                            continue
                        
                        cid = self.get_client_channel(clid)
                        if not clid or not cid:
                            continue
                        
                        name = self.get_client_nickname(clid)
                        is_afk_now, afk_reasons = self.check_afk_state(clid)
                        
                        current_users[clid] = {
                            'cid': cid,
                            'afk': is_afk_now
                        }
                        
                        # NEW USER
                        if clid not in old_users:
                            print(f"\n👤 JOINED: {name}")
                            
                            # Auto Server Group check
                            if AUTO_SGROUP_ENABLED:
                                self._give_normal_sgroup(clid, name)
                            
                            old_users[clid] = {
                                'cid': cid,
                                'original_cid': cid,
                                'afk': is_afk_now
                            }
                            
                            if is_afk_now:
                                self.afk_original_channels[clid] = cid
                            
                            if cid == move_me_cid:
                                print(f"   ⚠️ JOINED MOVE ME!")
                                notify_targets = self.get_notify_targets()
                                
                                if notify_targets:
                                    for t_clid, t_name in notify_targets.items():
                                        self.send_poke(t_clid, f"{name} Wants To Be Moved !")
                                    self.send_poke(clid, "Request Sent !")
                                    print(f"   ✅ Staff notified")
                                else:
                                    self.send_poke(clid, "No Staff Online !")
                            
                            if afk_cid and is_afk_now and cid != afk_cid:
                                reason_str = " & ".join(afk_reasons)
                                print(f"   💤 AFK: {reason_str} → Moving")
                                
                                # Track AFK move for spam detection
                                if not self._track_move(clid, "afk"):
                                    if self.move_client(clid, afk_cid):
                                        print(f"   ✅ Moved to AFK")
                                        self.send_poke(clid, f"Moved to AFK ({reason_str})")
                                        current_users[clid]['cid'] = afk_cid
                                else:
                                    print(f"   ⚠️ AFK move blocked - {MOVE_SPAM_BAN_REASON}")
                        
                        # EXISTING USER
                        elif clid in old_users:
                            old_state = old_users[clid]
                            
                            if old_state['cid'] != move_me_cid and cid == move_me_cid:
                                print(f"\n🔄 MOVE ME: {name}")
                                notify_targets = self.get_notify_targets()
                                
                                if notify_targets:
                                    for t_clid, t_name in notify_targets.items():
                                        self.send_poke(t_clid, f"{name} Wants To Be Moved !")
                                    self.send_poke(clid, "Request Sent !")
                                    print(f"   ✅ Staff notified")
                                else:
                                    self.send_poke(clid, "No Staff Online !")
                            
                            if afk_cid:
                                if not old_state['afk'] and is_afk_now:
                                    self.afk_original_channels[clid] = old_state['cid']
                                
                                if not old_state['afk'] and is_afk_now and cid != afk_cid:
                                    reason_str = " & ".join(afk_reasons)
                                    print(f"\n💤 AFK: {name} ({reason_str}) → Moving")
                                    
                                    # Track AFK move for spam detection
                                    if not self._track_move(clid, "afk"):
                                        if self.move_client(clid, afk_cid):
                                            print(f"   ✅ Moved to AFK")
                                            self.send_poke(clid, f"Moved to AFK ({reason_str})")
                                            current_users[clid]['cid'] = afk_cid
                                    else:
                                        print(f"   ⚠️ AFK move blocked - {MOVE_SPAM_BAN_REASON}")
                                
                                elif old_state['afk'] and not is_afk_now and self.return_from_afk:
                                    if clid in self.afk_original_channels:
                                        original_cid = self.afk_original_channels[clid]
                                        if original_cid and cid == afk_cid:
                                            orig_name = self.get_channel_name(original_cid)
                                            print(f"\n✅ RETURNED: {name} → {orig_name}")
                                            
                                            # Track return move for spam detection
                                            if not self._track_move(clid, "return"):
                                                if self.move_client(clid, original_cid):
                                                    print(f"   ✅ Moved back")
                                                    self.send_poke(clid, "Welcome back!")
                                                    current_users[clid]['cid'] = original_cid
                                                del self.afk_original_channels[clid]
                                            else:
                                                print(f"   ⚠️ Return move blocked - {MOVE_SPAM_BAN_REASON}")
                                                del self.afk_original_channels[clid]
                
                # Clean up sgroup tracking for disconnected users
                for clid in list(self.sgroup_given):
                    if clid not in current_users:
                        self.sgroup_given.discard(clid)
                
                for clid in list(self.afk_original_channels.keys()):
                    if clid not in current_users:
                        del self.afk_original_channels[clid]
                
                old_users = current_users
                time.sleep(CHECK_INTERVAL)
                
            except Exception as e:
                print(f"⚠️ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(3)
    
    def disconnect(self):
        try:
            self._send_raw("quit")
            self.sock.close()
            print("👋 Disconnected")
        except:
            pass


# ============================================
# MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 60)
    print(f"🤖 TeamSpeak Bot - {BOT_NICKNAME}")
    print("=" * 60)
    
    # Start Flask control panel in background
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start bot automatically
    print("\n🚀 Auto-starting bot...")
    try:
        bot_instance = TeamSpeakBot(
            host=SERVER_IP,
            port=QUERY_PORT,
            username=QUERY_USER,
            password=QUERY_PASS,
            server_id=SERVER_ID,
            nickname=BOT_NICKNAME
        )
        bot_start_time = time.time()
        bot_status = "online"
        
        print("\n📋 Channels:")
        channels = bot_instance.get_channel_list()
        for name, cid in channels.items():
            print(f"   CID {cid}: \"{name}\"")
        
        print("\n📋 Server Groups:")
        groups = bot_instance.get_server_groups()
        for sgid, name in groups.items():
            print(f"   SGID {sgid}: \"{name}\"")
        
        bot_instance.monitor()
        
    except KeyboardInterrupt:
        print("\n\n🛑 Bot stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        bot_status = "offline"
    finally:
        if bot_instance:
            bot_instance.disconnect()
