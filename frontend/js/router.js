/**
 * Hash-based 前端路由
 */

class Router {
  constructor() {
    this.routes = {};
    this.currentCleanup = null;
    window.addEventListener('hashchange', () => this._onHashChange());
  }

  register(hash, handler) {
    this.routes[hash] = handler;
  }

  start() {
    if (!window.location.hash) {
      window.location.hash = '#/portrait';
    } else {
      this._onHashChange();
    }
  }

  navigate(hash) {
    window.location.hash = hash;
  }

  _onHashChange() {
    const hash = window.location.hash || '#/portrait';

    // 更新导航栏高亮
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.getAttribute('href') === hash);
    });

    // 清理当前页面
    if (this.currentCleanup) {
      this.currentCleanup();
      this.currentCleanup = null;
    }

    // 匹配路由（支持参数）
    let handler = this.routes[hash];
    let params = {};

    if (!handler) {
      // 尝试匹配带参数的路由，如 #/interview/INT_12345678
      for (const [pattern, h] of Object.entries(this.routes)) {
        const regex = new RegExp('^' + pattern.replace(/:\w+/g, '([^/]+)') + '$');
        const match = hash.match(regex);
        if (match) {
          handler = h;
          const paramNames = (pattern.match(/:(\w+)/g) || []).map(p => p.slice(1));
          paramNames.forEach((name, i) => { params[name] = match[i + 1]; });
          break;
        }
      }
    }

    if (handler) {
      const content = document.getElementById('app-content');
      this.currentCleanup = handler(content, params);
    }
  }
}

const router = new Router();
