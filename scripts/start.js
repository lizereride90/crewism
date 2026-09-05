// npm start: single entrypoint — boots `python main.py`, which starts
// the bot first and then the dashboard UI itself.
const { spawn } = require('child_process');
const path = require('path');

const ROOT = path.join(__dirname, '..');

console.log('  ____ ____  _______        _____ ____  __  __');
console.log(' / ___|  _ \\| ____\\ \\      / /_ _/ ___||  \\/  |');
console.log('| |   | |_) |  _|  \\ \\ /\\ / / | |\\___ \\| |\\/| |');
console.log('| |___|  _ <| |___  \\ V  V /  | | ___) | |  | |');
console.log(' \\____|_| \\_|_____|  \\_/\\_/  |__|____/|_|  |_|');
console.log('');
console.log('[crewism] starting bot first, dashboard follows… (Ctrl+C stops both)');
console.log('');

const child = spawn('python3', ['main.py'], { cwd: ROOT, stdio: 'inherit', env: process.env });
child.on('exit', (code) => process.exit(code ?? 0));
process.on('SIGINT', () => { try { child.kill('SIGINT'); } catch {} });
process.on('SIGTERM', () => { try { child.kill('SIGTERM'); } catch {} });
