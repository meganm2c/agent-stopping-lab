// Read-only observer of the pinned runtime's effective session setting.
import {appendFileSync} from 'node:fs';
import {w as SettingsManager} from '../openclaw-feasibility/node_modules/openclaw/dist/resource-loader-RbH3J2C5.mjs';
const original=SettingsManager.prototype.getProviderRetrySettings;
SettingsManager.prototype.getProviderRetrySettings=function(...args){
  const settings=original.apply(this,args);
  appendFileSync(process.env.SPIKE_RETRY_SETTINGS,JSON.stringify({at:Date.now(),settings})+'\n');
  return settings;
};
