function doAtTime(timestamp, callback) {
  const now = performance.timeOrigin + performance.now();
  if (timestamp === null || timestamp - now <= 0) {
    callback();
  } else {
    setTimeout(callback, timestamp - now);
  }
}

export default { doAtTime };
