/**
 * Portrait 画像预览/编辑模块
 */

class ProfileManager {
  constructor() {
    this.profile = null;
    this.getMessages = null;
    this.contentEl = null;
  }

  init(container) {
    this.contentEl = container.querySelector('.profile-content');
    const exportBtn = container.querySelector('.btn-export');
    const editBtn = container.querySelector('.btn-edit');
    const saveBtn = container.querySelector('.btn-save-profile');

    if (exportBtn) exportBtn.addEventListener('click', () => this.exportJson());
    if (editBtn) editBtn.addEventListener('click', () => this.openEditor());
    if (saveBtn) saveBtn.addEventListener('click', () => this.saveToServer());

    this._showEmpty();
  }

  _showEmpty() {
    this.contentEl.innerHTML = `
      <div class="profile-empty">
        <div class="profile-empty-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
        </div>
        <h3>等待画像生成</h3>
        <p>在右侧与AI分析师对话，描述你的招聘需求。当信息足够时，输入"生成画像"即可查看结构化的人才画像。</p>
      </div>
    `;
  }

  updateProfile(profile) {
    this.profile = profile;
    this._render();
  }

  _render() {
    if (!this.profile) {
      this._showEmpty();
      return;
    }

    let html = '';

    if (this.profile.job_title || this.profile.company_context) {
      html += this._renderSection('基本信息', 'info', () => {
        let inner = '';
        if (this.profile.job_title) {
          inner += `<div class="context-item"><div class="context-label">岗位名称</div><div class="context-value">${this._escape(this.profile.job_title)}</div></div>`;
        }
        const ctx = this.profile.company_context || {};
        if (ctx.why_hire) {
          inner += `<div class="context-item"><div class="context-label">招聘原因</div><div class="context-value">${this._escape(ctx.why_hire)}</div></div>`;
        }
        if (ctx.team_description) {
          inner += `<div class="context-item"><div class="context-label">团队现状</div><div class="context-value">${this._escape(ctx.team_description)}</div></div>`;
        }
        if (ctx.business_context) {
          inner += `<div class="context-item"><div class="context-label">业务场景</div><div class="context-value">${this._escape(ctx.business_context)}</div></div>`;
        }
        return inner;
      });
    }

    if (this.profile.core_roles && this.profile.core_roles.length > 0) {
      html += this._renderSection('核心角色', 'roles', () => {
        return this.profile.core_roles.map(role => `
          <div class="role-card">
            <div class="role-name">${this._escape(role.role_name)}</div>
            ${role.description ? `<div class="role-desc">${this._escape(role.description)}</div>` : ''}
            ${role.key_responsibilities && role.key_responsibilities.length > 0 ? `
              <ul class="role-responsibilities">${role.key_responsibilities.map(r => `<li>${this._escape(r)}</li>`).join('')}</ul>
            ` : ''}
          </div>
        `).join('');
      });
    }

    if (this.profile.signal_dimensions && this.profile.signal_dimensions.length > 0) {
      html += this._renderSection('信号维度', 'signal', () => {
        return this.profile.signal_dimensions.map(cat => `
          <div class="signal-category">
            <div class="signal-category-title">${this._escape(cat.category)}</div>
            ${(cat.dimensions || []).map(dim => `
              <div class="signal-dimension">
                <div class="signal-dimension-name">
                  ${this._escape(dim.name)}
                  ${dim.weight ? `<span class="signal-dimension-weight ${this._getWeightClass(dim.weight)}">${this._escape(dim.weight)}</span>` : ''}
                </div>
                ${dim.description ? `<div class="signal-dimension-desc">${this._escape(dim.description)}</div>` : ''}
                ${dim.evaluation_criteria ? `<div class="signal-dimension-desc" style="margin-top:4px;"><strong>评估标准：</strong>${this._escape(dim.evaluation_criteria)}</div>` : ''}
              </div>
            `).join('')}
          </div>
        `).join('');
      });
    }

    if ((this.profile.must_have && this.profile.must_have.length > 0) ||
        (this.profile.nice_to_have && this.profile.nice_to_have.length > 0)) {
      html += this._renderSection('任职条件', 'conditions', () => {
        let inner = '';
        if (this.profile.must_have && this.profile.must_have.length > 0) {
          inner += `<div class="context-label" style="margin-bottom:8px;">必要条件</div>
            <div class="profile-tags">${this.profile.must_have.map(t => `<span class="profile-tag must-have">${this._escape(t)}</span>`).join('')}</div>`;
        }
        if (this.profile.nice_to_have && this.profile.nice_to_have.length > 0) {
          inner += `<div class="context-label" style="margin-top:16px;margin-bottom:8px;">加分项</div>
            <div class="profile-tags">${this.profile.nice_to_have.map(t => `<span class="profile-tag nice-to-have">${this._escape(t)}</span>`).join('')}</div>`;
        }
        return inner;
      });
    }

    if (this.profile.anti_profile && this.profile.anti_profile.length > 0) {
      html += this._renderSection('排除条件', 'anti', () => {
        return `<div class="profile-tags">${this.profile.anti_profile.map(t => `<span class="profile-tag anti">${this._escape(t)}</span>`).join('')}</div>`;
      });
    }

    if (this.profile.general_questions && this.profile.general_questions.length > 0) {
      html += this._renderSection('通用问题', 'questions', () => {
        return `<ol style="padding-left:20px;margin:0;">
          ${this.profile.general_questions.map(q => `<li style="font-size:13px;color:#475569;line-height:1.8;margin-bottom:4px;">${this._escape(q)}</li>`).join('')}
        </ol>`;
      });
    }

    this.contentEl.innerHTML = html;
  }

  _renderSection(title, icon, contentFn) {
    const icons = {
      info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4m0-4h.01"/></svg>`,
      roles: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87m-4-12a4 4 0 010 7.75"/></svg>`,
      signal: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>`,
      conditions: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3L22 4M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>`,
      anti: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M4.93 4.93l14.14 14.14"/></svg>`,
      questions: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3m.08 4h.01"/></svg>`,
    };
    return `
      <div class="profile-section">
        <div class="profile-section-header">
          <span class="profile-section-icon">${icons[icon] || icons.info}</span>
          <span class="profile-section-title">${title}</span>
        </div>
        ${contentFn()}
      </div>
    `;
  }

  _getWeightClass(weight) {
    if (weight === '核心') return 'core';
    if (weight === '重要') return 'important';
    return 'reference';
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  exportJson() {
    if (!this.profile) { showToast('暂无画像可导出', 'error'); return; }
    const json = JSON.stringify(this.profile, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `人才画像_${this.profile.job_title || '未命名'}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('画像已导出', 'success');
  }

  openEditor() {
    if (!this.profile) { showToast('暂无画像可编辑', 'error'); return; }

    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal edit-modal">
        <div class="modal-header">
          <div class="modal-title">编辑画像 JSON</div>
          <div class="modal-desc">直接修改JSON内容，保存后将更新画像预览</div>
        </div>
        <div class="modal-body">
          <textarea class="json-editor" id="json-editor-input">${JSON.stringify(this.profile, null, 2)}</textarea>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="edit-cancel-btn">取消</button>
          <button class="btn btn-primary" id="edit-save-btn">保存修改</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);

    overlay.querySelector('#edit-cancel-btn').addEventListener('click', () => overlay.remove());
    overlay.querySelector('#edit-save-btn').addEventListener('click', () => {
      try {
        const edited = JSON.parse(overlay.querySelector('#json-editor-input').value);
        this.profile = edited;
        this._render();
        overlay.remove();
        showToast('画像已更新', 'success');
      } catch (e) {
        showToast('JSON格式错误，请检查', 'error');
      }
    });
    overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
  }

  async saveToServer() {
    if (!this.profile) { showToast('暂无画像可保存', 'error'); return; }
    try {
      const messages = this.getMessages ? this.getMessages() : [];
      const data = await api.saveProfile(this.profile, messages);
      showToast(`画像保存成功 (ID: ${data.profile_id.slice(0, 8)}...)`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  getProfile() { return this.profile; }
}
