/* 前端入口：只做模块装配与启动，业务分别在各 feature 内。 */
import { registerView, startRouter } from './router.js';
import { bindSettings } from './features/settings/index.js';
import { chatBind, chatSync } from './features/chat/index.js';
import { bootCalc } from './features/calc/index.js';

registerView('chat', {sync: chatSync});
registerView('calc', {boot: bootCalc});

bindSettings();
chatBind();
startRouter();
