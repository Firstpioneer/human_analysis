/**
 * 聊天模块 — 管理对话界面
 */

class ChatManager {
  constructor() {
    this.messages = [];
    this.conversationId = null;
    this.isLoading = false;
    this.onProfileUpdate = null; // callback when profile is generated
    this._dirty = false; // 是否有未保存的更改

    this.messagesEl = document.getElementById('chat-messages');
    this.inputEl = document.getElementById('chat-input');
    this.sendBtnEl = document.getElementById('chat-send-btn');

    this._bindEvents();
    this._restoreState();
  }

  // 从 localStorage 恢复会话状态
  _restoreState() {
    try {
      const saved = localStorage.getItem('current_conversation');
      if (saved) {
        const state = JSON.parse(saved);
        if (state.conversationId && state.messages && state.messages.length > 0) {
          this.conversationId = state.conversationId;
          this._renderAllMessages(state.messages);
          this.messages = state.messages;
          return;
        }
      }
    } catch (e) {
      console.warn('恢复会话状态失败:', e);
      localStorage.removeItem('current_conversation');
    }
    this._showWelcome();
  }

  // 保存当前会话状态到 localStorage
  saveState() {
    if (this.messages.length > 0 && this.conversationId) {
      const state = {
        conversationId: this.conversationId,
        messages: this.messages,
        savedAt: new Date().toISOString()
      };
      localStorage.setItem('current_conversation', JSON.stringify(state));
      this._dirty = false;
    }
  }

  // 标记有未保存的更改
  markDirty() {
    this._dirty = true;
  }

  // 是否有未保存的更改
  isDirty() {
    return this._dirty;
  }

  _bindEvents() {
    this.sendBtnEl.addEventListener('click', (e) => {
      e.preventDefault();
      this.sendMessage();
    });

    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });

    // Auto-resize textarea
    this.inputEl.addEventListener('input', () => {
      this.inputEl.style.height = 'auto';
      this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 120) + 'px';
    });
  }

  _showWelcome() {
    const welcomeHtml = `
      <div class="message assistant">
        <div class="message-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
            <path d="M3 21v-2a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v2"/>
          </svg>
        </div>
        <div class="message-content">
          <p>你好！我是AI招聘画像分析师。</p>
          <p style="margin-top:8px;">你可以：</p>
          <p style="margin-top:4px;">1. 直接粘贴一段<strong>岗位描述（JD）</strong>，我会帮你解析并追问细节</p>
          <p style="margin-top:2px;">2. 或者直接用自然语言描述你的招聘需求</p>
          <p style="margin-top:8px;color:#94A3B8;font-size:12px;">对话过程中我会帮你挖掘真正的需求，最终生成结构化的人才画像。</p>
        </div>
      </div>
    `;
    this.messagesEl.innerHTML = welcomeHtml;
  }

  // 渲染所有消息（用于恢复会话，不触发滚动等副作用）
  _renderAllMessages(messages) {
    this.messagesEl.innerHTML = '';
    for (const msg of messages) {
      this._renderMessage(msg.role, msg.content);
    }
    this._scrollToBottom();
  }

  async sendMessage() {
    const text = this.inputEl.value.trim();
    if (!text || this.isLoading) return;

    if (!api.hasApiKey()) {
      showToast('请先设置 DeepSeek API Key', 'error');
      document.getElementById('api-key-btn').click();
      return;
    }

    // 添加用户消息
    this._addMessage('user', text);
    this.inputEl.value = '';
    this.inputEl.style.height = 'auto';
    this.markDirty();

    // 检测是否是生成画像的请求
    const PROFILE_KEYWORDS = [
      '生成画像', '生成人才画像', '开始生成', '输出画像',
      '画像生成', '人才画像', '生成一下', '可以生成',
      '确认生成', '开始画像', '输出人才', '生成吧',
      '整理画像', '汇总画像', '出画像',
      '帮我生成', '给我生成', '生成一个', '出一个画像',
    ];
    const shouldGenerateProfile = PROFILE_KEYWORDS.some(kw => text.includes(kw));

    // 显示加载状态
    this.isLoading = true;
    this.sendBtnEl.disabled = true;
    const typingEl = this._showTyping();

    try {
      const data = await api.chat(text, this.messages, this.conversationId, shouldGenerateProfile);

      // 移除加载状态
      typingEl.remove();

      // 添加助手回复到消息数组
      this._addMessage('assistant', data.reply);

      // 更新或设置 conversation_id（确保后续消息使用同一个ID）
      if (data.conversation_id) {
        this.conversationId = data.conversation_id;
      }

      // 保存状态到 localStorage（防止页面刷新/关闭丢失）
      this.saveState();

      // 如果有画像数据，更新预览
      if (data.profile_draft && this.onProfileUpdate) {
        this.onProfileUpdate(data.profile_draft);
      }
    } catch (err) {
      typingEl.remove();
      showToast(err.message, 'error');
    } finally {
      this.isLoading = false;
      this.sendBtnEl.disabled = false;
    }
  }

  _addMessage(role, content) {
    const timestamp = new Date().toISOString();
    this.messages.push({ role, content, timestamp });
    this._renderMessage(role, content);
    this._scrollToBottom();
  }

  _renderMessage(role, content) {
    const avatarSvg = role === 'assistant'
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
           <path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
           <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
           <path d="M3 21v-2a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v2"/>
         </svg>`
      : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
           <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
           <circle cx="12" cy="7" r="4"/>
         </svg>`;

    // 简单的 markdown 转换（加粗、换行）
    const htmlContent = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n/g, '<br>');

    const msgHtml = `
      <div class="message ${role}">
        <div class="message-avatar">${avatarSvg}</div>
        <div class="message-content">${htmlContent}</div>
      </div>
    `;
    this.messagesEl.insertAdjacentHTML('beforeend', msgHtml);
  }

  _showTyping() {
    const typingHtml = `
      <div class="message assistant typing-msg">
        <div class="message-avatar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2a4 4 0 0 1 4 4v1a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/>
            <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
            <path d="M3 21v-2a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4v2"/>
          </svg>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
          </div>
        </div>
      </div>
    `;
    this.messagesEl.insertAdjacentHTML('beforeend', typingHtml);
    this._scrollToBottom();
    return this.messagesEl.querySelector('.typing-msg');
  }

  _scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    });
  }

  getMessages() {
    return this.messages;
  }

  restoreMessages(messages, conversationId) {
    this.messages = [];
    this.messagesEl.innerHTML = '';
    if (conversationId) {
      this.conversationId = conversationId;
    }
    for (const msg of messages) {
      this.messages.push({ role: msg.role, content: msg.content, timestamp: msg.timestamp });
      this._renderMessage(msg.role, msg.content);
    }
    this._scrollToBottom();
    // 保存恢复后的状态到 localStorage
    this.saveState();
  }

  reset() {
    this.messages = [];
    this.conversationId = null;
    this._dirty = false;
    localStorage.removeItem('current_conversation');
    this._showWelcome();
  }
}
