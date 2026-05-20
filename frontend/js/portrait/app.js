/**
 * Portrait 模块入口 — 在 SPA 中初始化 portrait 页面
 */

class PortraitApp {
  constructor() {
    this.chatManager = null;
    this.profileManager = null;
    this.deletingId = null;
  }

  init(container) {
    container.innerHTML = `
      <div class="portrait-container">
        <!-- Left Panel: Profile -->
        <aside class="portrait-sidebar">
          <div class="panel-header">
            <div class="panel-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              人才画像
            </div>
            <div class="panel-actions">
              <button class="panel-action-btn btn-edit" title="编辑JSON">编辑</button>
              <button class="panel-action-btn btn-export" title="导出JSON">导出</button>
              <button class="panel-action-btn primary btn-save-profile" title="保存到服务器">保存</button>
            </div>
          </div>
          <div class="profile-content"></div>
        </aside>

        <!-- Right Panel: Chat -->
        <section class="chat-panel">
          <div class="chat-messages"></div>
          <div class="chat-input-area">
            <div class="chat-input-wrapper">
              <textarea class="chat-input" placeholder="粘贴JD文本，或描述你的招聘需求..." rows="1"></textarea>
              <button type="button" class="chat-send-btn" title="发送">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"/>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
              </button>
            </div>
            <div class="chat-input-hint">
              <span>按 Enter 发送，Shift+Enter 换行</span>
              <button type="button" class="generate-profile-btn" title="基于当前对话生成结构化人才画像">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                  <polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/>
                  <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                生成画像
              </button>
            </div>
          </div>
        </section>
      </div>

      <!-- History Panel -->
      <div class="history-panel" id="history-panel">
        <div class="history-header">
          <span class="history-title">历史画像</span>
          <button class="history-close" id="history-close">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="history-list" id="history-list">
          <div class="history-empty">暂无保存的画像</div>
        </div>
      </div>
    `;

    // Initialize modules
    this.chatManager = new ChatManager();
    this.profileManager = new ProfileManager();
    this.chatManager.init(container);
    this.profileManager.init(container);

    this.chatManager.onProfileUpdate = (profile) => {
      this.profileManager.updateProfile(profile);
    };
    this.profileManager.getMessages = () => this.chatManager.getMessages();

    // Bind portrait-specific nav buttons
    this._bindNavButtons(container);

    // Check API key
    if (!api.hasApiKey()) {
      setTimeout(() => this._showApiKeyModal(), 500);
    }

    // Generate profile button
    container.querySelector('.generate-profile-btn').addEventListener('click', () => {
      this._generateProfile();
    });

    // Return cleanup function
    return () => {
      this.chatManager.destroy();
    };
  }

  _bindNavButtons(container) {
    // History
    const historyPanel = document.getElementById('history-panel');
    const historyClose = document.getElementById('history-close');
    historyClose.addEventListener('click', () => historyPanel.classList.remove('open'));

    // Add nav buttons to main nav
    this._addPortraitNavButtons();
  }

  _addPortraitNavButtons() {
    // Remove existing portrait buttons if any
    document.querySelectorAll('.portrait-nav-btn').forEach(b => b.remove());

    const navRight = document.querySelector('.nav-right');
    if (!navRight) return;

    const btns = [
      { id: 'new-chat-btn', icon: `<path d="M12 5v14m-7-7h14"/>`, label: '新对话' },
      { id: 'save-chat-btn', icon: `<path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>`, label: '保存' },
      { id: 'history-btn', icon: `<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>`, label: '历史' },
      { id: 'api-key-btn', icon: `<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>`, label: 'API Key' },
    ];

    btns.forEach(({ id, icon, label }) => {
      const btn = document.createElement('button');
      btn.className = 'portrait-nav-btn nav-btn';
      btn.id = id;
      btn.title = label;
      btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">${icon}</svg>`;
      btn.style.cssText = 'display:flex;align-items:center;gap:6px;padding:6px 12px;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.15);border-radius:6px;color:white;font-size:12px;cursor:pointer;';
      navRight.insertBefore(btn, navRight.firstChild);
    });

    // Bind events
    document.getElementById('new-chat-btn').addEventListener('click', () => {
      this.chatManager.reset();
      this.profileManager.updateProfile(null);
      showToast('已开始新对话', 'info');
    });

    document.getElementById('save-chat-btn').addEventListener('click', () => this._saveCurrentChat());

    document.getElementById('history-btn').addEventListener('click', () => {
      const panel = document.getElementById('history-panel');
      if (panel.classList.contains('open')) {
        panel.classList.remove('open');
      } else {
        panel.classList.add('open');
        this._loadHistoryList();
      }
    });

    document.getElementById('api-key-btn').addEventListener('click', () => this._showApiKeyModal());
  }

  _showApiKeyModal() {
    const existing = document.querySelector('.modal-overlay');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal">
        <div class="modal-header">
          <div class="modal-title">设置 API Key</div>
          <div class="modal-desc">请输入你的 DeepSeek API Key，用于驱动AI对话</div>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label" for="api-key-input">DeepSeek API Key</label>
            <input type="password" class="form-input" id="api-key-input" placeholder="sk-..." value="${api.getApiKey() || ''}">
            <div class="form-hint">Key 仅保存在浏览器本地，不会上传到任何服务器</div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="api-cancel-btn">取消</button>
          <button class="btn btn-primary" id="api-save-btn">保存</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    const input = overlay.querySelector('#api-key-input');
    input.focus();
    input.select();

    overlay.querySelector('#api-save-btn').addEventListener('click', () => {
      const key = input.value.trim();
      if (!key) { showToast('请输入 API Key', 'error'); return; }
      api.setApiKey(key);
      overlay.remove();
      showToast('API Key 已保存', 'success');
    });

    overlay.querySelector('#api-cancel-btn').addEventListener('click', () => overlay.remove());
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') overlay.querySelector('#api-save-btn').click(); });
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  }

  async _loadHistoryList() {
    const listEl = document.getElementById('history-list');
    listEl.innerHTML = '<div class="history-empty">加载中...</div>';
    try {
      const data = await api.listConversations();
      if (data.conversations.length === 0) {
        listEl.innerHTML = '<div class="history-empty">暂无历史对话</div>';
        return;
      }
      listEl.innerHTML = data.conversations.map(conv => `
        <div class="history-item" data-id="${conv.id}">
          <div class="history-item-row">
            <div class="history-item-info">
              <div class="history-item-title">${this._escape(conv.job_title)}</div>
              <div class="history-item-meta">
                ${conv.message_count} 条消息
                ${conv.has_profile ? ' · 含画像' : ''}
                · ${conv.updated_at ? new Date(conv.updated_at).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}
              </div>
            </div>
            <button class="history-delete-btn" data-id="${conv.id}" title="删除此对话">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            </button>
          </div>
        </div>
      `).join('');

      listEl.querySelectorAll('.history-item-info').forEach(info => {
        info.addEventListener('click', async () => {
          const id = info.closest('.history-item').dataset.id;
          await this._loadConversation(id);
        });
      });

      listEl.querySelectorAll('.history-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          this._showDeleteConfirm(btn.dataset.id);
        });
      });
    } catch (err) {
      listEl.innerHTML = `<div class="history-empty">加载失败: ${err.message}</div>`;
    }
  }

  async _loadConversation(id) {
    try {
      const conv = await api.getConversation(id);
      if (conv.messages && conv.messages.length > 0) {
        this.chatManager.restoreMessages(conv.messages, conv.id);
      }
      if (conv.profile_draft) {
        this.profileManager.updateProfile(conv.profile_draft);
      }
      document.getElementById('history-panel').classList.remove('open');
      showToast('已加载历史对话', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  _showDeleteConfirm(id) {
    this.deletingId = id;
    const existing = document.querySelector('.modal-overlay.delete-confirm');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay delete-confirm';
    overlay.innerHTML = `
      <div class="modal" style="width:380px;">
        <div class="modal-header">
          <div class="modal-title">确认删除</div>
          <div class="modal-desc">删除后不可恢复，确定要删除这条历史对话吗？</div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="delete-cancel-btn">取消</button>
          <button class="btn btn-danger" id="delete-confirm-btn">确认删除</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    overlay.querySelector('#delete-cancel-btn').addEventListener('click', () => {
      this.deletingId = null;
      overlay.remove();
    });

    overlay.querySelector('#delete-confirm-btn').addEventListener('click', async () => {
      if (!this.deletingId) return;
      const idToDelete = this.deletingId;
      this.deletingId = null;
      overlay.remove();
      try {
        await api.deleteConversation(idToDelete);
        showToast('对话已删除', 'success');
        await this._loadHistoryList();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) { this.deletingId = null; overlay.remove(); }
    });
  }

  async _saveCurrentChat() {
    const messages = this.chatManager.getMessages();
    const conversationId = this.chatManager.conversationId;
    if (!messages || messages.length === 0) { showToast('当前没有对话内容可保存', 'info'); return; }
    try {
      const profile = this.profileManager.getProfile();
      const jobTitle = profile?.job_title || messages.find(m => m.role === 'user')?.content.slice(0, 50) || '未命名对话';
      const result = await api.saveConversation(conversationId, messages, profile, jobTitle);
      if (result.conversation_id && !conversationId) {
        this.chatManager.conversationId = result.conversation_id;
      }
      this.chatManager.saveState();
      showToast('对话已保存', 'success');
    } catch (err) {
      this.chatManager.saveState();
      showToast('已保存到本地，服务器保存失败: ' + err.message, 'error');
    }
  }

  async _generateProfile() {
    const messages = this.chatManager.getMessages();
    const conversationId = this.chatManager.conversationId;
    if (!messages || messages.length === 0) { showToast('请先进行对话，再生成画像', 'info'); return; }
    if (!api.hasApiKey()) { showToast('请先设置 API Key', 'error'); this._showApiKeyModal(); return; }

    const btn = document.querySelector('.generate-profile-btn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    showToast('正在生成人才画像...', 'info');

    try {
      const data = await api.generateProfile(messages, conversationId);
      if (data && data.profile) {
        this.profileManager.updateProfile(data.profile);
      } else {
        showToast('画像数据为空，请重试', 'error');
      }

      if (data.conversation_id) {
        this.chatManager.conversationId = data.conversation_id;
      }

      this.chatManager._addMessage('assistant', '人才画像已生成！请在左侧查看预览，你可以要求修改任何部分，或者确认保存。');

      const profile = data.profile;
      const jobTitle = profile?.job_title || messages.find(m => m.role === 'user')?.content.slice(0, 50) || '未命名对话';
      try {
        await api.saveConversation(this.chatManager.conversationId, this.chatManager.getMessages(), profile, jobTitle);
      } catch (e) { console.warn('自动保存对话失败:', e); }

      this.chatManager.saveState();
      showToast('人才画像已生成！', 'success');
    } catch (err) {
      showToast('画像生成失败: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
        </svg>
        生成画像
      `;
    }
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

// 注册为全局模块
window.portraitApp = new PortraitApp();
