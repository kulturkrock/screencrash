function doAtTime(timestamp, callback) {
  const now = Date.now();
  if (timestamp === null || timestamp - now <= 0) {
    callback();
  } else {
    setTimeout(callback, timestamp - now);
  }
}

export default { doAtTime };
