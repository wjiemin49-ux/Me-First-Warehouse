const electron = require('electron');
console.log('electron keys', Object.keys(electron));
console.log('app type', typeof electron.app);
if (electron.app) {
  console.log('has lock fn', typeof electron.app.requestSingleInstanceLock);
  electron.app.quit();
}
