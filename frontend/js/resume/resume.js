/**
 * 简历分析模块
 */

class ResumeModule {
  constructor() {
    this.results = [];
  }

  init(container) {
    container.innerHTML = `
      <div class="resume-container">
        <div class="resume-header">
          <h1>简历分析</h1>
          <p>上传简历文件，AI 自动解析并提取关键信息</p>
        </div>

        <div class="upload-card">
          <div class="upload-zone" id="upload-zone">
            <div class="upload-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <h3>拖拽文件到此处，或点击上传</h3>
            <p>支持 PDF、DOCX 格式，最大 10MB</p>
            <input type="file" id="file-input" accept=".pdf,.docx" style="display:none;">
          </div>
          <div class="upload-progress" id="upload-progress">
            <div class="progress-bar-bg"><div class="progress-bar-fill" id="progress-fill"></div></div>
            <div class="progress-text" id="progress-text">解析中...</div>
          </div>
        </div>

        <div class="resume-results" id="resume-results"></div>
      </div>
    `;

    this._bindEvents(container);
    this._loadResults(container);

    return () => {};
  }

  _bindEvents(container) {
    const zone = container.querySelector('#upload-zone');
    const fileInput = container.querySelector('#file-input');

    zone.addEventListener('click', () => fileInput.click());

    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('dragover');
    });

    zone.addEventListener('dragleave', () => {
      zone.classList.remove('dragover');
    });

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('dragover');
      const file = e.dataTransfer.files[0];
      if (file) this._uploadFile(file, container);
    });

    fileInput.addEventListener('change', () => {
      const file = fileInput.files[0];
      if (file) this._uploadFile(file, container);
      fileInput.value = '';
    });
  }

  async _uploadFile(file, container) {
    const progress = container.querySelector('#upload-progress');
    const progressFill = container.querySelector('#progress-fill');
    const progressText = container.querySelector('#progress-text');

    progress.classList.add('active');
    progressFill.style.width = '30%';
    progressText.textContent = `正在上传 ${file.name}...`;

    try {
      progressFill.style.width = '60%';
      progressText.textContent = 'AI 解析中，请稍候...';

      const result = await api.parseResume(file);

      progressFill.style.width = '100%';
      progressText.textContent = '解析完成！';

      showToast(`简历 "${file.name}" 解析成功`, 'success');

      setTimeout(() => {
        progress.classList.remove('active');
        progressFill.style.width = '0%';
      }, 1500);

      this._loadResults(container);
    } catch (err) {
      progressFill.style.width = '0%';
      progressText.textContent = '解析失败';
      showToast('简历解析失败: ' + err.message, 'error');
      setTimeout(() => progress.classList.remove('active'), 2000);
    }
  }

  async _loadResults(container) {
    const resultsEl = container.querySelector('#resume-results');
    try {
      const data = await api.listResumeResults();
      if (!data.results || data.results.length === 0) {
        resultsEl.innerHTML = '';
        return;
      }

      this.results = data.results;
      resultsEl.innerHTML = `
        <h3 style="font-family:var(--font-display);font-size:16px;margin-bottom:var(--space-4);color:var(--color-foreground);">已解析的简历</h3>
        ${data.results.map(r => {
          const parsed = r.parsed_data || {};
          const name = r.resume_id ? r.resume_id.replace(/\.\w+$/, '') : '未知';
          const experiences = (parsed.objective_experiences || []).length;
          const claims = (parsed.claims || []).length;
          const github = parsed.digital_footprint?.github_url || '';
          return `
            <div class="resume-result-card" data-id="${r.resume_id}">
              <div class="resume-result-header">
                <span class="resume-result-title">${this._escape(name)}</span>
                <span class="resume-result-badge">${experiences} 段经历 · ${claims} 项技能</span>
              </div>
              <div class="resume-result-info">
                ${parsed.objective_experiences?.slice(0, 2).map(e => `${e.company} - ${e.title}`).join(' | ') || '暂无经历信息'}
                ${github ? `<br>GitHub: ${this._escape(github)}` : ''}
              </div>
              <div class="resume-result-actions">
                <button class="resume-btn" onclick="window.resumeModule.viewDetail('${r.resume_id}')">查看详情</button>
                <button class="resume-btn delete" onclick="window.resumeModule.deleteResult('${r.resume_id}')">删除</button>
              </div>
            </div>
          `;
        }).join('')}
      `;
    } catch (err) {
      console.error('加载简历结果失败:', err);
    }
  }

  async viewDetail(id) {
    try {
      const data = await api.getResumeResult(id);
      const parsed = data.parsed_data || {};

      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.innerHTML = `
        <div class="modal resume-detail-modal">
          <div class="modal-header">
            <div class="modal-title">简历详情 - ${this._escape(id)}</div>
          </div>
          <div class="resume-detail-content">
            ${this._renderDetailSection('经历', (parsed.objective_experiences || []).map(e =>
              `<div class="resume-item"><strong>${this._escape(e.company)}</strong> - ${this._escape(e.title)}<br>${this._escape(e.description || '')}</div>`
            ).join('') || '<div class="resume-item">暂无</div>')}

            ${this._renderDetailSection('技能声明', (parsed.claims || []).map(c =>
              `<div class="resume-item">${this._escape(c.content || '')}</div>`
            ).join('') || '<div class="resume-item">暂无</div>')}

            ${parsed.digital_footprint ? this._renderDetailSection('数字足迹', `
              <div class="resume-item">
                GitHub: ${this._escape(parsed.digital_footprint.github_url || '无')}<br>
                公开仓库: ${parsed.digital_footprint.public_repos || 0}<br>
                Followers: ${parsed.digital_footprint.followers || 0}<br>
                主要语言: ${(parsed.digital_footprint.top_languages || []).map(l => l[0]).join(', ') || '无'}
              </div>
            `) : ''}

            ${data.blind_spots && data.blind_spots.length > 0 ? this._renderDetailSection('盲点分析',
              data.blind_spots.map(b => `<div class="resume-item">${this._escape(b)}</div>`).join('')
            ) : ''}
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" id="detail-close-btn">关闭</button>
          </div>
        </div>
      `;

      document.body.appendChild(overlay);
      overlay.querySelector('#detail-close-btn').addEventListener('click', () => overlay.remove());
      overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
    } catch (err) {
      showToast('加载详情失败: ' + err.message, 'error');
    }
  }

  _renderDetailSection(title, content) {
    if (!content) return '';
    return `
      <div class="resume-section">
        <h4>${title}</h4>
        ${content}
      </div>
    `;
  }

  async deleteResult(id) {
    if (!confirm('确定删除此简历解析结果？')) return;
    try {
      // No delete API yet, just reload
      showToast('删除功能暂未实现', 'info');
    } catch (err) {
      showToast(err.message, 'error');
    }
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

window.resumeModule = new ResumeModule();
