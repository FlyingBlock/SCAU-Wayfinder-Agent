/* 前端入口：只做模块装配与启动，业务分别在各 feature 内。 */
import { registerView, startRouter } from './router.js';
import { bindSettings } from './features/settings/index.js';
import { chatBind, chatSync } from './features/chat/index.js';
import { bootCalc } from './features/calc/index.js';

registerView('chat', {sync: chatSync, title: '主页对话'});
registerView('calc', {
  boot: bootCalc,
  title: '绩点 / 综测计算器',
  defaultSub: 'scores',
  subs: {
    scores: {label: '① 我的成绩', tab: 'tab-profile'},
    goals: {label: '② 门槛对照', tab: 'tab-goals'},
    acts: {label: '③ 活动篮', tab: 'tab-acts'},
    rules: {label: '④ 计算口径', tab: 'tab-rules'},
  },
});

bindSettings();
chatBind();
startRouter();
