#tr:
# Bu uygulama, aynı Wi-Fi ağı üzerindeki cihazlar arasında dosya göndermek ve almak için basit bir araçtır. 
# Bir cihazda sunucu başlatabilir ve diğer cihazlardan bu sunucuya dosya gönderebilirsiniz. 
# Sunucu, gelen dosyaları kaydeder ve web tarayıcısı üzerinden erişilebilir hale getirir.
# Gerekli kütüphaneler: 
# tkinter, http.server, socket, threading, mimetypes, os, json,
# urllib, webbrowser, pathlib, html, argparse, sys
# USerXerai tarafından yapılmıştır. İyi kullanımlar! =)


#en: 
# This application is a simple tool for sending and receiving files between devices on the same Wi-Fi network. 
# You can start a server on one device and send files to that server from other devices. 
# The server saves incoming files and makes them accessible through a web browser.
# Required libraries:
# tkinter, http.server, socket, threading, mimetypes, os, json,
# urllib, webbrowser, pathlib, html, argparse, sys
# Made by USerXerai. Enjoy! =)




#!/usr/bin/env python3

import argparse
import html
import json
import mimetypes
import os
import socket
import sys
import threading
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import Tk, ttk, StringVar, filedialog, messagebox, scrolledtext
from urllib.parse import urlparse

RECEIVE_DIR = Path("received")
DEFAULT_PORT = 5050
PAGE_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LocalSend - Dosya Alıcı</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: auto; }
    h1 { color: #333; }
    .box { border: 1px solid #ccc; padding: 18px; border-radius: 10px; margin-bottom: 18px; }
    input[type=file] { width: 100%; }
    button { padding: 10px 16px; font-size: 1rem; }
    ul { list-style: none; padding-left: 0; }
    li { margin-bottom: 6px; }
    a { color: #1a73e8; text-decoration: none; }
  </style>
</head>
<body>
  <h1>LocalSend Dosya Alıcı</h1>
  <div class="box">
    <p>Bu makineye <strong>Wi-Fi ağındaki başka bir cihazdan</strong> dosya göndermek için aşağıdaki formu kullanabilirsiniz.</p>
    <form action="/upload" method="post" enctype="multipart/form-data">
      <input type="file" name="files" multiple required><br><br>
      <button type="submit">Gönder</button>
    </form>
  </div>
  <div class="box">
    <h2>Gelen Dosyalar</h2>
    <ul id="file-list"></ul>
  </div>
  <script>
    async function loadFiles() {
      const res = await fetch('/list');
      const files = await res.json();
      const list = document.getElementById('file-list');
      list.innerHTML = '';
      if (files.length === 0) {
        list.innerHTML = '<li>Henüz dosya yok.</li>';
        return;
      }
      for (const file of files) {
        const li = document.createElement('li');
        li.innerHTML = `<a href="/download/${encodeURIComponent(file)}" target="_blank">${file}</a>`;
        list.appendChild(li);
      }
    }
    loadFiles();
  </script>
</body>
</html>"""

PAGE_HTML_EN = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LocalSend - File Receiver</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: auto; }
    h1 { color: #333; }
    .box { border: 1px solid #ccc; padding: 18px; border-radius: 10px; margin-bottom: 18px; }
    input[type=file] { width: 100%; }
    button { padding: 10px 16px; font-size: 1rem; }
    ul { list-style: none; padding-left: 0; }
    li { margin-bottom: 6px; }
    a { color: #1a73e8; text-decoration: none; }
  </style>
</head>
<body>
  <h1>LocalSend File Receiver</h1>
  <div class="box">
    <p>Use the form below to send files from another device on the same Wi-Fi network to this machine.</p>
    <form action="/upload" method="post" enctype="multipart/form-data">
      <input type="file" name="files" multiple required><br><br>
      <button type="submit">Send</button>
    </form>
  </div>
  <div class="box">
    <h2>Received Files</h2>
    <ul id="file-list"></ul>
  </div>
  <script>
    async function loadFiles() {
      const res = await fetch('/list');
      const files = await res.json();
      const list = document.getElementById('file-list');
      list.innerHTML = '';
      if (files.length === 0) {
        list.innerHTML = '<li>No files yet.</li>';
        return;
      }
      for (const file of files) {
        const li = document.createElement('li');
        li.innerHTML = `<a href="/download/${encodeURIComponent(file)}" target="_blank">${file}</a>`;
        list.appendChild(li);
      }
    }
    loadFiles();
  </script>
</body>
</html>"""

WEB_PAGE_LANG = 'tr'


def get_page_html(lang):
    return PAGE_HTML if lang == 'tr' else PAGE_HTML_EN


def get_local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 80))
        return sock.getsockname()[0]
    except OSError:
        return '127.0.0.1'
    finally:
        sock.close()


def safe_filename(name: str) -> str:
    name = os.path.basename(name)
    return name.replace('/', '_').replace('..', '_')


class LocalSendHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='text/html; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self._set_headers()
            self.wfile.write(get_page_html(WEB_PAGE_LANG).encode('utf-8'))
            return

        if parsed.path == '/list':
            self._set_headers(200, 'application/json; charset=utf-8')
            files = [f.name for f in sorted(RECEIVE_DIR.glob('*')) if f.is_file()]
            self.wfile.write(json.dumps(files).encode('utf-8'))
            return

        if parsed.path.startswith('/download/'):
            file_name = os.path.basename(parsed.path[len('/download/'):])
            file_name = urllib.parse.unquote(file_name)
            file_path = RECEIVE_DIR / safe_filename(file_name)
            if file_path.exists() and file_path.is_file():
                mime_type, _ = mimetypes.guess_type(str(file_path))
                self.send_response(200)
                self.send_header('Content-Type', mime_type or 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{html.escape(file_path.name)}"')
                self.send_header('Content-Length', str(file_path.stat().st_size))
                self.end_headers()
                with file_path.open('rb') as f:
                    self.wfile.write(f.read())
                return
            self.send_error(404, 'Dosya bulunamadı')
            return

        self.send_error(404, 'Sayfa bulunamadı')

    def do_POST(self):
        if self.path != '/upload':
            self.send_error(404, 'Sayfa bulunamadı')
            return

        content_type = self.headers.get('Content-Type', '')
        if not content_type.startswith('multipart/form-data'):
            self.send_error(400, 'multipart/form-data bekleniyor')
            return

        content_length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(content_length)
        fields = parse_multipart_form_data(content_type, body)

        uploaded = []
        for item in fields:
            if item['name'] != 'files' or not item['filename']:
                continue
            filename = safe_filename(item['filename'])
            target = RECEIVE_DIR / filename
            if target.exists():
                base, ext = os.path.splitext(filename)
                suffix = 1
                while (RECEIVE_DIR / f'{base}_{suffix}{ext}').exists():
                    suffix += 1
                target = RECEIVE_DIR / f'{base}_{suffix}{ext}'
            with target.open('wb') as out_file:
                out_file.write(item['value'])
            uploaded.append(target.name)

        self._set_headers()
        response = '<html><body><h1>Yüklendi</h1><p>Gelen dosyalar:</p><ul>'
        for name in uploaded:
            response += f'<li>{html.escape(name)}</li>'
        response += '</ul><p><a href="/">Geri dön</a></p></body></html>'
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        return


def parse_multipart_form_data(content_type: str, body: bytes):
    boundary = None
    for part in content_type.split(';'):
        part = part.strip()
        if part.startswith('boundary='):
            boundary = part.split('=', 1)[1]
            if boundary.startswith('"') and boundary.endswith('"'):
                boundary = boundary[1:-1]
            break
    if not boundary:
        raise ValueError('Boundary bulunamadı')

    boundary_bytes = boundary.encode('utf-8')
    delimiter = b'--' + boundary_bytes
    parts = body.split(delimiter)
    fields = []

    for part in parts:
        if not part or part == b'--' or part == b'--\r\n':
            continue
        if part.startswith(b'\r\n'):
            part = part[2:]
        if part.endswith(b'\r\n'):
            part = part[:-2]

        headers, sep, value = part.partition(b'\r\n\r\n')
        if not sep:
            continue

        header_lines = headers.decode('utf-8', 'replace').split('\r\n')
        field_name = None
        filename = None
        for header in header_lines:
            header = header.strip()
            if header.lower().startswith('content-disposition:'):
                disposition = header.split(':', 1)[1].strip()
                for item in disposition.split(';'):
                    item = item.strip()
                    if item.startswith('name='):
                        field_name = item.split('=', 1)[1].strip('"')
                    elif item.startswith('filename='):
                        filename = item.split('=', 1)[1].strip('"')
        fields.append({'name': field_name, 'filename': filename, 'value': value})

    return fields


LANGUAGES = {
    'tr': 'Türkçe',
    'en': 'English',
}

TRANSLATIONS = {
    'tr': {
        'app_title': 'USerXerai - Wi-Fi Dosya Aktarımı',
        'tab_server': 'Sunucu',
        'tab_send': 'Gönder',
        'tab_settings': 'Ayarlar',
        'server_settings_frame': 'Sunucu Ayarları',
        'port_label': 'Port:',
        'start_button': 'Başlat',
        'stop_button': 'Durdur',
        'open_browser': 'Tarayıcıda Aç',
        'server_stopped': 'Sunucu durdu',
        'server_running': 'Çalışıyor:',
        'received_files_frame': 'Gelen Dosyalar',
        'file_name_header': 'Dosya Adı',
        'refresh_button': 'Yenile',
        'target_settings_frame': 'Hedef Ayarları',
        'target_label': 'Hedef IP,PORT',
        'choose_files_button': 'Dosya Seç',
        'send_button': 'Gönder',
        'selected_files_frame': 'Seçilen Dosyalar',
        'status_messages_frame': 'Durum Mesajları',
        'app_info_frame': 'Uygulama Bilgisi',
        'version_label': 'Versiyon',
        'description_label': 'Açıklama: Bu uygulama aynı Wi-Fi ağı üzerindeki cihazlar arasında dosya gönderip almanıza yarar.',
        'author_label': 'USerXerai tarafından yapılmıştır.',
        'theme_settings_frame': 'Tema Ayarları',
        'light_theme': 'Açık Tema',
        'dark_theme': 'Karanlık Tema',
        'language_settings_frame': 'Dil Ayarları',
        'choose_theme_label': 'Tema seçin:',
        'language_label': 'Dil seçin:',
        'theme_note': '(Tema değişikliği anında uygulanacaktır.)',
        'language_note': '(Dil değişikliği anında uygulanacaktır.)',
        'language_turkish': 'Turkish',
        'language_english': 'English',
        'error_title': 'Hata',
        'port_open_error': 'Port açılamadı:',
        'valid_port_error': 'Geçerli bir port girin.',
        'target_required_error': 'Hedef IP:PORT girin.',
        'files_required_error': 'Önce gönderilecek dosyaları seçin.',
        'choose_files_dialog': 'Göndermek istediğiniz dosyaları seçin',
        'files_selected_status': '{count} dosya seçildi.',
        'sending_status': 'Gönderiliyor...',
        'sent_status': 'Gönderildi.',
        'send_error_status': 'Gönderme hatası.',
        'server_started_log': 'Sunucu başlatıldı:',
        'server_stopped_log': 'Sunucu durduruldu.',
    },
    'en': {
        'app_title': 'USerXerai - Wi-Fi File Transfer',
        'tab_server': 'Server',
        'tab_send': 'Send',
        'tab_settings': 'Settings',
        'server_settings_frame': 'Server Settings',
        'port_label': 'Port:',
        'start_button': 'Start',
        'stop_button': 'Stop',
        'open_browser': 'Open in Browser',
        'server_stopped': 'Server stopped',
        'server_running': 'Running:',
        'received_files_frame': 'Received Files',
        'refresh_button': 'Refresh',
        'target_settings_frame': 'Destination Settings',
        'target_label': 'Target IP,PORT',
        'choose_files_button': 'Select Files',
        'send_button': 'Send',
        'selected_files_frame': 'Selected Files',
        'status_messages_frame': 'Status Messages',
        'app_info_frame': 'App Information',
        'version_label': 'Version',
        'description_label': 'This app helps transfer files between devices on the same Wi-Fi network.',
        'author_label': 'Made by USerXerai.',
        'theme_settings_frame': 'Theme Settings',
        'light_theme': 'Light Theme',
        'dark_theme': 'Dark Theme',
        'language_settings_frame': 'Language Settings',
        'choose_theme_label': 'Choose theme:',
        'language_label': 'Choose language:',
        'theme_note': '(Theme changes apply immediately.)',
        'language_note': '(Language changes apply immediately.)',
        'language_turkish': 'Turkish',
        'language_english': 'English',
        'error_title': 'Error',
        'port_open_error': 'Could not open port:',
        'valid_port_error': 'Enter a valid port.',
        'target_required_error': 'Enter the target IP:PORT.',
        'files_required_error': 'Select files to send first.',
        'choose_files_dialog': 'Select files to send',
        'files_selected_status': '{count} file(s) selected.',
        'sending_status': 'Sending...',
        'sent_status': 'Sent.',
        'send_error_status': 'Send failed.',
        'server_started_log': 'Server started:',
        'server_stopped_log': 'Server stopped.',
    },
}


def get_text(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS['tr']).get(key, key)


class LocalSendApp(Tk):
    def __init__(self):
        super().__init__()
        self.title('USerXerai - Wi-Fi Dosya Aktarımı')
        self.geometry('800x600')
        self.resizable(False, False)
        self.server = None
        self.server_thread = None
        self.server_url = ''
        self.file_paths = []
        self.theme = StringVar(value='light')
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        self.create_widgets()
        self.apply_theme()

    def get_text(self, key):
        return TRANSLATIONS.get(self.language.get(), TRANSLATIONS['tr']).get(key, key)

    def create_widgets(self):
        self.language = StringVar(value='tr')

        self.notebook = ttk.Notebook(self)
        self.server_tab = ttk.Frame(self.notebook)
        self.send_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.server_tab, text=self.get_text('tab_server'))
        self.notebook.add(self.send_tab, text=self.get_text('tab_send'))
        self.notebook.add(self.settings_tab, text=self.get_text('tab_settings'))
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.server_status = StringVar(value=self.get_text('server_stopped'))
        self.server_port = StringVar(value=str(DEFAULT_PORT))
        self.target_address = StringVar(value='')
        self.target_status = StringVar(value='')

        self.server_top = ttk.Labelframe(self.server_tab, text=self.get_text('server_settings_frame'))
        self.server_top.pack(fill='x', padx=10, pady=10)
        self.server_port_label = ttk.Label(self.server_top, text=self.get_text('port_label'))
        self.server_port_label.grid(row=0, column=0, sticky='w', padx=6, pady=6)
        ttk.Entry(self.server_top, textvariable=self.server_port, width=12).grid(row=0, column=1, sticky='w', padx=6, pady=6)
        self.server_button = ttk.Button(self.server_top, text=self.get_text('start_button'), command=self.toggle_server)
        self.server_button.grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.open_button = ttk.Button(self.server_top, text=self.get_text('open_browser'), command=self.open_browser, state='disabled')
        self.open_button.grid(row=0, column=3, sticky='w', padx=6, pady=6)
        ttk.Label(self.server_top, textvariable=self.server_status, foreground='blue').grid(row=1, column=0, columnspan=4, sticky='w', padx=6, pady=6)

        self.files_frame = ttk.Labelframe(self.server_tab, text=self.get_text('received_files_frame'))
        self.files_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.file_list = ttk.Treeview(self.files_frame, columns=('name',), show='headings', height=12)
        self.file_list.heading('name', text=self.get_text('file_name_header'))
        self.file_list.column('name', width=700)
        self.file_list.pack(side='left', fill='both', expand=True, padx=(6,0), pady=6)
        scrollbar = ttk.Scrollbar(self.files_frame, orient='vertical', command=self.file_list.yview)
        scrollbar.pack(side='right', fill='y', padx=(0,6), pady=6)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.refresh_button = ttk.Button(self.server_tab, text=self.get_text('refresh_button'), command=self.refresh_file_list)
        self.refresh_button.pack(anchor='e', padx=16, pady=(0,8))

        self.send_top = ttk.Labelframe(self.send_tab, text=self.get_text('target_settings_frame'))
        self.send_top.pack(fill='x', padx=10, pady=10)
        self.target_label = ttk.Label(self.send_top, text=self.get_text('target_label'))
        self.target_label.grid(row=0, column=0, sticky='w', padx=6, pady=6)
        ttk.Entry(self.send_top, textvariable=self.target_address, width=30).grid(row=0, column=1, sticky='w', padx=6, pady=6)
        self.choose_button = ttk.Button(self.send_top, text=self.get_text('choose_files_button'), command=self.choose_files)
        self.choose_button.grid(row=0, column=2, sticky='w', padx=6, pady=6)
        self.send_button = ttk.Button(self.send_top, text=self.get_text('send_button'), command=self.send_files_gui)
        self.send_button.grid(row=0, column=3, sticky='w', padx=6, pady=6)
        ttk.Label(self.send_top, textvariable=self.target_status, foreground='green').grid(row=1, column=0, columnspan=4, sticky='w', padx=6, pady=6)

        self.selected_frame = ttk.Labelframe(self.send_tab, text=self.get_text('selected_files_frame'))
        self.selected_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.select_text = scrolledtext.ScrolledText(self.selected_frame, height=12, wrap='word', state='disabled')
        self.select_text.pack(fill='both', expand=True, padx=6, pady=6)

        self.log_frame = ttk.Labelframe(self.send_tab, text=self.get_text('status_messages_frame'))
        self.log_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=8, wrap='word', state='disabled')
        self.log_text.pack(fill='both', expand=True, padx=6, pady=6)

        self.settings_app_frame = ttk.Labelframe(self.settings_tab, text=self.get_text('app_info_frame'))
        self.settings_app_frame.pack(fill='x', padx=10, pady=10)
        self.version_label = ttk.Label(self.settings_app_frame, text=f"{self.get_text('version_label')}: 1.0")
        self.version_label.pack(anchor='w', padx=10, pady=4)
        self.description_label = ttk.Label(self.settings_app_frame, text=self.get_text('description_label'))
        self.description_label.pack(anchor='w', padx=10, pady=4)
        self.author_label = ttk.Label(self.settings_app_frame, text=self.get_text('author_label'))
        self.author_label.pack(anchor='w', padx=10, pady=4)

        self.settings_theme_frame = ttk.Labelframe(self.settings_tab, text=self.get_text('theme_settings_frame'))
        self.settings_theme_frame.pack(fill='x', padx=10, pady=10)
        self.theme_label = ttk.Label(self.settings_theme_frame, text=self.get_text('choose_theme_label'))
        self.theme_label.grid(row=0, column=0, sticky='w', padx=10, pady=6)
        ttk.Radiobutton(self.settings_theme_frame, text=self.get_text('light_theme'), variable=self.theme, value='light', command=self.apply_theme).grid(row=1, column=0, sticky='w', padx=16, pady=2)
        ttk.Radiobutton(self.settings_theme_frame, text=self.get_text('dark_theme'), variable=self.theme, value='dark', command=self.apply_theme).grid(row=2, column=0, sticky='w', padx=16, pady=2)
        self.theme_note_label = ttk.Label(self.settings_theme_frame, text=self.get_text('theme_note'))
        self.theme_note_label.grid(row=3, column=0, sticky='w', padx=10, pady=6)

        self.settings_lang_frame = ttk.Labelframe(self.settings_tab, text=self.get_text('language_settings_frame'))
        self.settings_lang_frame.pack(fill='x', padx=10, pady=10)
        self.language_label = ttk.Label(self.settings_lang_frame, text=self.get_text('language_label'))
        self.language_label.grid(row=0, column=0, sticky='w', padx=10, pady=6)
        self.language_radio_tr = ttk.Radiobutton(self.settings_lang_frame, text=self.get_text('language_turkish'), variable=self.language, value='tr', command=self.apply_language)
        self.language_radio_tr.grid(row=1, column=0, sticky='w', padx=16, pady=2)
        self.language_radio_en = ttk.Radiobutton(self.settings_lang_frame, text=self.get_text('language_english'), variable=self.language, value='en', command=self.apply_language)
        self.language_radio_en.grid(row=2, column=0, sticky='w', padx=16, pady=2)
        self.language_note_label = ttk.Label(self.settings_lang_frame, text=self.get_text('language_note'))
        self.language_note_label.grid(row=3, column=0, sticky='w', padx=10, pady=6)

        self.apply_language()

    def apply_language(self):
        lang = self.language.get()
        global WEB_PAGE_LANG
        WEB_PAGE_LANG = lang

        self.title(self.get_text('app_title'))
        self.notebook.tab(self.server_tab, text=self.get_text('tab_server'))
        self.notebook.tab(self.send_tab, text=self.get_text('tab_send'))
        self.notebook.tab(self.settings_tab, text=self.get_text('tab_settings'))
        self.server_top.config(text=self.get_text('server_settings_frame'))
        self.server_port_label.config(text=self.get_text('port_label'))
        self.server_button.config(text=self.get_text('stop_button') if self.server else self.get_text('start_button'))
        self.open_button.config(text=self.get_text('open_browser'))
        self.files_frame.config(text=self.get_text('received_files_frame'))
        self.file_list.heading('name', text=self.get_text('file_name_header'))
        self.refresh_button.config(text=self.get_text('refresh_button'))
        self.send_top.config(text=self.get_text('target_settings_frame'))
        self.target_label.config(text=self.get_text('target_label'))
        self.choose_button.config(text=self.get_text('choose_files_button'))
        self.send_button.config(text=self.get_text('send_button'))
        self.selected_frame.config(text=self.get_text('selected_files_frame'))
        self.log_frame.config(text=self.get_text('status_messages_frame'))
        self.settings_app_frame.config(text=self.get_text('app_info_frame'))
        self.version_label.config(text=f"{self.get_text('version_label')}: 1.0")
        self.description_label.config(text=self.get_text('description_label'))
        self.author_label.config(text=self.get_text('author_label'))
        self.settings_theme_frame.config(text=self.get_text('theme_settings_frame'))
        self.theme_label.config(text=self.get_text('choose_theme_label'))
        self.theme_note_label.config(text=self.get_text('theme_note'))
        self.settings_lang_frame.config(text=self.get_text('language_settings_frame'))
        self.language_label.config(text=self.get_text('language_label'))
        self.language_radio_tr.config(text=self.get_text('language_turkish'))
        self.language_radio_en.config(text=self.get_text('language_english'))
        self.language_note_label.config(text=self.get_text('language_note'))
        if self.server:
            self.server_status.set(f"{self.get_text('server_running')} {self.server_url}")
        else:
            self.server_status.set(self.get_text('server_stopped'))

    def log(self, message: str):
        self.log_text.configure(state='normal')
        self.log_text.insert('end', message + '\n')
        self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def apply_theme(self):
        theme = self.theme.get()
        if theme == 'dark':
            bg = '#242f3f'
            fg = '#e9eef4'
            alt = '#33415b'
            entry_bg = '#2f3b52'
            text_bg = '#283344'
            button_bg = '#3f506c'
            button_hover = '#506180'
            border = '#3a4a64'
        else:
            bg = '#eef5fb'
            fg = '#26343f'
            alt = '#d8e6f2'
            entry_bg = '#fbfeff'
            text_bg = '#f7fbff'
            button_bg = '#d3e1f4'
            button_hover = '#b9d4ef'
            border = '#d3dde8'

        self.configure(bg=bg)
        self.style.configure('TFrame', background=bg)
        self.style.configure('TLabel', background=bg, foreground=fg, font=('Segoe UI', 10))
        self.style.configure('TButton', background=button_bg, foreground=fg, borderwidth=0, padding=8, font=('Segoe UI', 10))
        self.style.map('TButton', background=[('active', button_hover)])
        self.style.configure('TLabelframe', background=bg, foreground=fg, borderwidth=1, relief='solid')
        self.style.configure('TLabelframe.Label', background=bg, foreground=fg, font=('Segoe UI', 10, 'bold'))
        self.style.configure('TEntry', fieldbackground=entry_bg, background=entry_bg, foreground=fg, bordercolor=border, lightcolor=border, darkcolor=border, relief='flat')
        self.style.configure('TRadiobutton', background=bg, foreground=fg, font=('Segoe UI', 10))
        self.style.configure('Treeview', background=entry_bg, fieldbackground=entry_bg, foreground=fg, bordercolor=border, rowheight=28)
        self.style.configure('Treeview.Heading', background=alt, foreground=fg, relief='flat', font=('Segoe UI', 10, 'bold'))
        self.style.configure('TNotebook', background=bg, borderwidth=0)
        self.style.configure('TNotebook.Tab', background=alt, foreground=fg, padding=[10, 8])
        self.style.map('TNotebook.Tab', background=[('selected', bg)])

        if hasattr(self, 'select_text'):
            self.select_text.configure(background=text_bg, foreground=fg, insertbackground=fg, relief='flat', bd=0)
        if hasattr(self, 'log_text'):
            self.log_text.configure(background=text_bg, foreground=fg, insertbackground=fg, relief='flat', bd=0)

    def toggle_server(self):
        if self.server:
            self.stop_server()
        else:
            try:
                port = int(self.server_port.get())
            except ValueError:
                messagebox.showerror(self.get_text('error_title'), self.get_text('valid_port_error'))
                return
            self.start_server(port)

    def start_server(self, port: int):
        RECEIVE_DIR.mkdir(exist_ok=True)
        server_address = ('', port)
        try:
            self.server = ThreadingHTTPServer(server_address, LocalSendHandler)
        except OSError as exc:
            messagebox.showerror(self.get_text('error_title'), f"{self.get_text('port_open_error')} {exc}")
            self.server = None
            return
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        local_ip = get_local_ip()
        self.server_url = f'http://{local_ip}:{port}'
        self.server_status.set(f"{self.get_text('server_running')} {self.server_url}")
        self.server_button.config(text=self.get_text('stop_button'))
        self.open_button.config(state='normal')
        self.log(f"{self.get_text('server_started_log')} {self.server_url}")
        self.refresh_file_list()

    def stop_server(self):
        if not self.server:
            return
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=2)
        self.server = None
        self.server_thread = None
        self.server_status.set(self.get_text('server_stopped'))
        self.server_button.config(text=self.get_text('start_button'))
        self.open_button.config(state='disabled')
        self.log(self.get_text('server_stopped_log'))

    def open_browser(self):
        if self.server_url:
            webbrowser.open(self.server_url)

    def refresh_file_list(self):
        self.file_list.delete(*self.file_list.get_children())
        RECEIVE_DIR.mkdir(exist_ok=True)
        for f in sorted(RECEIVE_DIR.glob('*')):
            if f.is_file():
                self.file_list.insert('', 'end', values=(f.name,))

    def choose_files(self):
        paths = filedialog.askopenfilenames(title=self.get_text('choose_files_dialog'))
        if paths:
            self.file_paths = list(paths)
            self.select_text.configure(state='normal')
            self.select_text.delete('1.0', 'end')
            for p in self.file_paths:
                self.select_text.insert('end', p + '\n')
            self.select_text.configure(state='disabled')
            self.target_status.set(self.get_text('files_selected_status').format(count=len(self.file_paths)))

    def send_files_gui(self):
        target = self.target_address.get().strip()
        if not target:
            messagebox.showerror(self.get_text('error_title'), self.get_text('target_required_error'))
            return
        if not self.file_paths:
            messagebox.showerror(self.get_text('error_title'), self.get_text('files_required_error'))
            return
        self.target_status.set(self.get_text('sending_status'))
        threading.Thread(target=self._send_files_thread, args=(target, list(self.file_paths)), daemon=True).start()

    def _send_files_thread(self, target, files):
        try:
            result = send_files(target, files)
            self.after(0, lambda: self.target_status.set(self.get_text('sent_status')))
            self.after(0, lambda: self.log(f"{self.get_text('sent_status')} {target}"))
            self.after(0, lambda: self.log(result))
        except Exception as exc:
            self.after(0, lambda: self.target_status.set(self.get_text('send_error_status')))
            self.after(0, lambda: self.log(f"{self.get_text('error_title')}: {exc}"))


def run_server(port: int):
    RECEIVE_DIR.mkdir(exist_ok=True)
    server_address = ('', port)
    httpd = ThreadingHTTPServer(server_address, LocalSendHandler)
    local_ip = get_local_ip()
    print('=== LocalSend Sunucusu ===')
    print(f'Ağdaki tüm cihazlar için erişim adresi: http://{local_ip}:{port}')
    print('Alınan dosyalar klasörü:', RECEIVE_DIR.resolve())
    print('Web tarayıcınızdan adresi açın ve dosya gönderin.')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nSunucu kapatıldı.')
        httpd.server_close()


def build_multipart(files):
    boundary = '----LocalSendBoundary' + str(os.getpid())
    body = bytearray()
    for path in files:
        path = Path(path)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f'Dosya bulunamadı: {path}')
        filename = path.name
        mimetype = mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'.encode('utf-8'))
        body.extend(f'Content-Type: {mimetype}\r\n\r\n'.encode('utf-8'))
        body.extend(path.read_bytes())
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    content_type = f'multipart/form-data; boundary={boundary}'
    return bytes(body), content_type


def send_files(target: str, file_paths):
    if ':' not in target:
        raise ValueError('Hedef adresi şu formatta olmalı: 192.168.x.x:8080')
    url = f'http://{target}/upload'
    body, content_type = build_multipart(file_paths)
    request = urllib.request.Request(url, data=body, method='POST')
    request.add_header('Content-Type', content_type)
    request.add_header('Content-Length', str(len(body)))

    with urllib.request.urlopen(request, timeout=60) as response:
        text = response.read().decode('utf-8', errors='ignore')
        return f'Sunucu yanıtı: {response.status} {response.reason}\n{text}'


def parse_args():
    parser = argparse.ArgumentParser(description='LocalSend benzeri Wi-Fi dosya aktarım aracı')
    subparsers = parser.add_subparsers(dest='command')

    serve_parser = subparsers.add_parser('serve', help='Dosya alma sunucusunu başlat')
    serve_parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Sunucu portu (varsayılan 8080)')

    send_parser = subparsers.add_parser('send', help='Dosya gönder')
    send_parser.add_argument('target', help='Hedef sunucu adresi, örn: 192.168.1.5:8080')
    send_parser.add_argument('files', nargs='+', help='Gönderilecek dosyalar')

    args = parser.parse_args()
    if len(sys.argv) == 1:
        return None
    return args


def main():
    args = parse_args()
    if args is None:
        try:
            app = LocalSendApp()
            app.mainloop()
        except Exception as exc:
            print('GUI başlatılamadı:', exc)
            print('Komut satırı modunu kullanmak için `python aktarım.py serve` veya `python aktarım.py send ...` çalıştırın.')
        return

    if args.command == 'serve':
        run_server(args.port)
    elif args.command == 'send':
        print(send_files(args.target, args.files))


if __name__ == '__main__':
    main() 
#                                                                                      made by USerXerai =)