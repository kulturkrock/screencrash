// Config file, uses require imports
// eslint-disable-next-line @typescript-eslint/no-var-requires
const path = require("path");

module.exports = {
  files: path.resolve(__dirname, "./dist/**/*"),
  ghostMode: false, // Don't mirror click events etc.
  injectChanges: true,
  logFileChanges: true,
  logLevel: "info",
  notify: true,
  reloadDelay: 200,
  server: {
    baseDir: path.resolve(__dirname, "./dist"),
  },
  startPath: `/?core=${encodeURIComponent(
    process.env.CORE || "localhost:8001",
  )}`,
};
