"use strict";

const {contextBridge, ipcRenderer} = require("electron");

contextBridge.exposeInMainWorld("kamyDesktop", Object.freeze({
  isDesktop: true,
  platform: process.platform,
  setExpanded: value => ipcRenderer.invoke("kamy:set-expanded", Boolean(value)),
  toggleExpanded: () => ipcRenderer.invoke("kamy:toggle-expanded"),
  quit: () => ipcRenderer.invoke("kamy:quit"),
  onModeChange: callback => {
    if (typeof callback !== "function") return () => {};
    const listener = (_event, detail) => callback(detail);
    ipcRenderer.on("kamy:mode-changed", listener);
    return () => ipcRenderer.removeListener("kamy:mode-changed", listener);
  }
}));
