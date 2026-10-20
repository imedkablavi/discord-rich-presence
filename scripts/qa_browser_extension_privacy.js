#!/usr/bin/env node
"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("browser_extension/content.js", "utf8");

function runContentScript({ isPrivate }) {
  const messages = [];
  const runtimeListeners = [];
  const doc = {
    title: "Secret page title",
    visibilityState: "visible",
    documentElement: {},
    hasFocus: () => true,
    querySelectorAll: () => [],
    querySelector: () => null,
    addEventListener: () => {},
  };
  const api = {
    extension: { inIncognitoContext: isPrivate },
    runtime: {
      sendMessage: (message) => {
        messages.push(message);
        return Promise.resolve();
      },
      onMessage: { addListener: (listener) => runtimeListeners.push(listener) },
    },
  };
  const context = {
    browser: api,
    navigator: { userAgent: "Mozilla/5.0 Firefox/121.0" },
    document: doc,
    location: {
      hostname: "accounts.example.test",
      href: "https://accounts.example.test/profile/private-user?token=not-for-disclosure",
    },
    window: { addEventListener: () => {} },
    MutationObserver: class {
      observe() {}
      disconnect() {}
    },
    setTimeout: () => 1,
    clearTimeout: () => {},
    setInterval: () => 1,
    console,
  };
  vm.runInNewContext(source, context, { filename: "browser_extension/content.js" });
  assert.equal(messages.length, 1, "initial snapshot should be published");
  assert.equal(messages[0].type, "cybrex.activity");
  return { snapshot: messages[0].snapshot, runtimeListeners };
}

const privateSnapshot = runContentScript({ isPrivate: true }).snapshot;
assert.equal(privateSnapshot.private, true);
assert.equal(privateSnapshot.browser, "Firefox");
assert.equal(privateSnapshot.focused, true);
assert.equal(privateSnapshot.visible, true);
for (const forbidden of ["url", "title", "service", "media"]) {
  assert.equal(
    Object.hasOwn(privateSnapshot, forbidden),
    false,
    `private snapshots must not include ${forbidden}`,
  );
}

const normalSnapshot = runContentScript({ isPrivate: false }).snapshot;
assert.equal(normalSnapshot.private, false);
assert.equal(normalSnapshot.url, "https://accounts.example.test/profile/private-user?token=not-for-disclosure");
assert.equal(normalSnapshot.title, "Secret page title");
assert.equal(typeof normalSnapshot.media, "object");

console.log("Browser Companion private-snapshot contract passed.");
