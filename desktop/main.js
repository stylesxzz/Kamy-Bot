"use strict";

const path = require("node:path");
const {app, BrowserWindow, ipcMain, session, shell} = require("electron");

const targetUrl = process.argv.find(value => /^http:\/\/(127\.0\.0\.1|localhost):\d+/.test(value));
if (!targetUrl) {
  console.error("Kamy Desktop: URL local do servidor não foi informada.");
  app.quit();
}

const isWayland = process.platform === "linux" &&
  (/wayland/i.test(process.env.XDG_SESSION_TYPE || "") ||
   Boolean(process.env.WAYLAND_DISPLAY));
let mainWindow = null;
let expanded = false;
let compactBounds = null;

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });
}

function setExpanded(next) {
  if (!mainWindow || mainWindow.isDestroyed()) return expanded;
  const desired = Boolean(next);
  if (desired === expanded) return expanded;

  if (desired) {
    compactBounds = mainWindow.getBounds();
    expanded = true;
    mainWindow.setAlwaysOnTop(false);
    mainWindow.setFullScreen(true);
  } else {
    expanded = false;
    if (mainWindow.isFullScreen()) mainWindow.setFullScreen(false);
    if (mainWindow.isMaximized()) mainWindow.unmaximize();

    const restore = compactBounds || {width: 440, height: 620};
    setTimeout(() => {
      if (!mainWindow || mainWindow.isDestroyed() || expanded) return;
      mainWindow.setBounds({
        ...restore,
        width: Math.max(380, Math.min(480, restore.width || 440)),
        height: Math.max(500, Math.min(760, restore.height || 620))
      });
      if (!isWayland) mainWindow.setAlwaysOnTop(true, "floating");
      mainWindow.show();
    }, 180);
  }

  mainWindow.webContents.send("kamy:mode-changed", {expanded});
  return expanded;
}

function createWindow() {
  if (isWayland) {
    console.warn("Kamy: o Wayland pode impedir a janela de ficar sempre no topo.");
  }

  mainWindow = new BrowserWindow({
    width: 440,
    height: 620,
    minWidth: 360,
    minHeight: 480,
    maxWidth: 720,
    show: false,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: true,
    movable: true,
    fullscreenable: true,
    autoHideMenuBar: true,
    title: "Kamy Bot",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true
    }
  });

  if (!isWayland) mainWindow.setAlwaysOnTop(true, "floating");

  mainWindow.webContents.setWindowOpenHandler(({url}) => {
    if (/^https:\/\//i.test(url)) shell.openExternal(url);
    return {action: "deny"};
  });

  mainWindow.webContents.on("will-navigate", (event, destination) => {
    const local = destination.startsWith("http://127.0.0.1:") ||
      destination.startsWith("http://localhost:");
    if (!local) event.preventDefault();
  });

  mainWindow.once("ready-to-show", () => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.loadURL(targetUrl).catch(error => {
    console.error("Não foi possível abrir a interface local do Kamy:", error.message);
    app.quit();
  });
}

ipcMain.handle("kamy:set-expanded", (event, value) => {
  if (!mainWindow || event.sender !== mainWindow.webContents) return expanded;
  return setExpanded(value);
});

ipcMain.handle("kamy:toggle-expanded", event => {
  if (!mainWindow || event.sender !== mainWindow.webContents) return expanded;
  return setExpanded(!expanded);
});

ipcMain.handle("kamy:quit", event => {
  if (mainWindow && event.sender !== mainWindow.webContents) return false;
  app.quit();
  return true;
});

app.whenReady().then(() => {
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const origin = details?.requestingUrl || webContents.getURL();
    const local = origin.startsWith("http://127.0.0.1:") ||
      origin.startsWith("http://localhost:");
    callback(local && permission === "media");
  });

  session.defaultSession.setPermissionCheckHandler((_webContents, permission, origin) => {
    return permission === "media" &&
      (origin.startsWith("http://127.0.0.1:") || origin.startsWith("http://localhost:"));
  });

  createWindow();
});

app.on("window-all-closed", () => {
  app.quit();
});
