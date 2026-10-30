import "./index.css";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

const rootElement = document.getElementById("root");
if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

// Single, robust Service Worker registration for offline PWA operation
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        console.log("SyncPulse PWA Service Worker registered:", reg.scope);
      })
      .catch((err) => {
        console.warn("SyncPulse Service Worker registration note:", err);
      });
  });
}
