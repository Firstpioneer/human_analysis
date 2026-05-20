/**
 * 主应用逻辑
 */

// 全局 Toast 通知
function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// 应用初始化
class App {
  constructor() {
    this.chatManager = null;
    this.profileManager = null;
    this.deletingId = null; // 正在删除的对话ID

    this._initModules();
    this._bindGlobalEvents();
    this._checkApiKey();
    this._setupAutoSave();
  }

  _initModules() {
    this.chatManager = new ChatManager();
    this.profileManager = new ProfileManager();

    // 当画像生成时，更新预览
    this.chatManager.onProfileUpdate = (profile) => {
      this.profileManager.updateProfile(profile);
    };

    // 让 ProfileManager 能获取当前对话消息
    this.profileManager.getMessages = () => this.chatManager.getMessages();
  }

  _bindGlobalEvents() {
    // API Key 按钮
    document.getElementById('api-key-btn').addEventListener('click', () => this._showApiKeyModal());

    // 历史按钮
    document.getElementById('history-btn').addEventListener('click', () => this._toggleHistory());

    // 新对话按钮
    document.getElementById('new-chat-btn').addEventListener('click', () => {
      this.chatManager.reset();
      this.profileManager.updateProfile(null);
      showToast('已开始新对话', 'info');
    });

    // 保存对话按钮
    document.getElementById('save-chat-btn').addEventListener('click', () => this._saveCurrentChat());

    // 生成画像按钮（直接调用 /api/generate-profile，绕过关键词检测）
    document.getElementById('generate-profile-btn').addEventListener('click', () => this._generateProfile());
  }

  _checkApiKey() {
    if (!api.hasApiKey()) {
      setTimeout(() => this._showApiKeyModal(), 500);
    }
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
            <input type="password" class="form-input" id="api-key-input"
                   placeholder="sk-..." value="${api.getApiKey() || ''}">
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
      if (!key) {
        showToast('请输入 API Key', 'error');
        return;
      }
      api.setApiKey(key);
      overlay.remove();
      showToast('API Key 已保存', 'success');
    });

    overlay.querySelector('#api-cancel-btn').addEventListener('click', () => {
      overlay.remove();
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        overlay.querySelector('#api-save-btn').click();
      }
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) overlay.remove();
    });
  }

  // ---- 历史面板 ----

  async _toggleHistory() {
    const panel = document.getElementById('history-panel');
    const isOpen = panel.classList.contains('open');

    if (isOpen) {
      panel.classList.remove('open');
      return;
    }

    panel.classList.add('open');
    await this._loadHistoryList();
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
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
              </svg>
            </button>
          </div>
        </div>
      `).join('');

      // 点击加载对话
      listEl.querySelectorAll('.history-item-info').forEach(info => {
        info.addEventListener('click', async () => {
          const item = info.closest('.history-item');
          const id = item.dataset.id;
          await this._loadConversation(id);
        });
      });

      // 点击删除
      listEl.querySelectorAll('.history-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const id = btn.dataset.id;
          this._showDeleteConfirm(id);
        });
      });
    } catch (err) {
      listEl.innerHTML = `<div class="history-empty">加载失败: ${err.message}</div>`;
    }
  }

  async _loadConversation(id) {
    try {
      const conv = await api.getConversation(id);

      // 恢复对话记录
      if (conv.messages && conv.messages.length > 0) {
        this.chatManager.restoreMessages(conv.messages, conv.id);
      }

      // 恢复画像
      if (conv.profile_draft) {
        this.profileManager.updateProfile(conv.profile_draft);
      }

      document.getElementById('history-panel').classList.remove('open');
      showToast('已加载历史对话', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  // ---- 删除确认 ----

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
        // 刷新列表
        await this._loadHistoryList();
      } catch (err) {
        showToast(err.message, 'error');
      }
    });

    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        this.deletingId = null;
        overlay.remove();
      }
    });
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async _saveCurrentChat() {
    const messages = this.chatManager.getMessages();
    const conversationId = this.chatManager.conversationId;

    if (!messages || messages.length === 0) {
      showToast('当前没有对话内容可保存', 'info');
      return;
    }

    try {
      const profile = this.profileManager.getProfile();
      const jobTitle = profile?.job_title || messages.find(m => m.role === 'user')?.content.slice(0, 50) || '未命名对话';

      const result = await api.saveConversation(
        conversationId,
        messages,
        profile,
        jobTitle
      );

      // 确保 conversationId 已更新（后端可能返回新ID）
      if (result.conversation_id && !conversationId) {
        this.chatManager.conversationId = result.conversation_id;
      }

      // 同步保存到 localStorage
      this.chatManager.saveState();

      showToast('对话已保存', 'success');
    } catch (err) {
      // 即使后端保存失败，也保存到 localStorage 作为备份
      this.chatManager.saveState();
      showToast('已保存到本地，服务器保存失败: ' + err.message, 'error');
    }
  }

  // ---- 生成画像（直接调用专用接口）----

  async _generateProfile() {
    const messages = this.chatManager.getMessages();
    const conversationId = this.chatManager.conversationId;

    if (!messages || messages.length === 0) {
      showToast('请先进行对话，再生成画像', 'info');
      return;
    }

    if (!api.hasApiKey()) {
      showToast('请先设置 API Key', 'error');
      this._showApiKeyModal();
      return;
    }

    const btn = document.getElementById('generate-profile-btn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    showToast('正在生成人才画像...', 'info');

    try {
      const data = await api.generateProfile(messages, conversationId);
      console.log('[DEBUG] generateProfile 返回数据:', JSON.stringify(data).slice(0, 500));
      console.log('[DEBUG] data 类型:', typeof data, 'keys:', data ? Object.keys(data) : 'null');

      // 更新画像预览
      if (data && data.profile) {
        console.log('[DEBUG] 调用 updateProfile, profile keys:', Object.keys(data.profile));
        this.profileManager.updateProfile(data.profile);
        console.log('[DEBUG] updateProfile 完成');
      } else {
        console.warn('[DEBUG] data.profile 为空, data:', JSON.stringify(data).slice(0, 200));
        showToast('画像数据为空，请重试', 'error');
      }

      // 更新 conversationId（后端可能返回新的）
      if (data.conversation_id) {
        this.chatManager.conversationId = data.conversation_id;
      }

      // 在聊天窗口添加提示消息
      this.chatManager._addMessage('assistant', '人才画像已生成！请在左侧查看预览，你可以要求修改任何部分，或者确认保存。');

      // 自动保存对话（含画像）
      const profile = data.profile;
      const jobTitle = profile?.job_title || messages.find(m => m.role === 'user')?.content.slice(0, 50) || '未命名对话';
      try {
        await api.saveConversation(
          this.chatManager.conversationId,
          this.chatManager.getMessages(),
          profile,
          jobTitle
        );
      } catch (e) {
        console.warn('自动保存对话失败:', e);
      }

      this.chatManager.saveState();
      showToast('人才画像已生成！', 'success');
    } catch (err) {
      console.error('[DEBUG] generateProfile 异常:', err);
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

  _setupAutoSave() {
    // 页面卸载前自动保存到后端
    window.addEventListener('beforeunload', () => {
      // 确保 localStorage 已同步（最终防线）
      this.chatManager.saveState();

      const messages = this.chatManager.getMessages();
      const conversationId = this.chatManager.conversationId;

      if (messages && messages.length > 0 && conversationId) {
        const profile = this.profileManager.getProfile();
        const jobTitle = profile?.job_title || messages.find(m => m.role === 'user')?.content.slice(0, 50) || '未命名对话';

        // 使用 sendBeacon 进行异步保存（页面卸载时也能发送）
        const data = JSON.stringify({
          conversation_id: conversationId,
          messages: messages,
          profile_draft: profile,
          job_title: jobTitle
        });

        navigator.sendBeacon(
          'http://localhost:8000/api/conversations',
          new Blob([data], { type: 'application/json' })
        );
      }
    });

    // 页面可见性变化时自动保存（切换标签页、最小化等）
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.chatManager.saveState();
      }
    });

    // 定期自动保存到 localStorage（每30秒）
    setInterval(() => {
      if (this.chatManager.isDirty()) {
        this.chatManager.saveState();
      }
    }, 30000);
  }
}

// 启动应用
document.addEventListener('DOMContentLoaded', () => {
  window.app = new App();
});
