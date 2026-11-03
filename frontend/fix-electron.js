const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const os = require('os');

const electronDir = path.join(__dirname, 'node_modules', 'electron');
const pathTxt = path.join(electronDir, 'path.txt');

if (os.platform() === 'darwin') {
  const relativePath = 'Electron.app/Contents/MacOS/Electron';
  const execPath = path.join(electronDir, 'dist', relativePath);
  
  // Verify if binary exists and framework symlink is intact
  let needsFix = !fs.existsSync(execPath) || !fs.existsSync(pathTxt);
  if (!needsFix) {
    try {
      execSync(`"${execPath}" -v`, { stdio: 'ignore' });
    } catch {
      needsFix = true;
    }
  }

  if (needsFix) {
    const homedir = os.homedir();
    const cacheDir = path.join(homedir, 'Library', 'Caches', 'electron');
    if (fs.existsSync(cacheDir)) {
      try {
        const findCmd = `find "${cacheDir}" -name "electron-v*-darwin-*.zip" | head -n 1`;
        const zipFile = execSync(findCmd, { encoding: 'utf-8' }).trim();
        if (zipFile && fs.existsSync(zipFile)) {
          const distDir = path.join(electronDir, 'dist');
          fs.rmSync(distDir, { recursive: true, force: true });
          fs.mkdirSync(distDir, { recursive: true });
          execSync(`unzip -q "${zipFile}" -d "${distDir}"`);
          fs.writeFileSync(pathTxt, relativePath, 'utf-8');
          console.log('Repaired Electron binary and symlinks via native unzip.');
        }
      } catch (err) {
        console.warn('Auto-repair failed:', err.message);
      }
    }
  } else {
    fs.writeFileSync(pathTxt, relativePath, 'utf-8');
  }
}

