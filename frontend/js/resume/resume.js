/**
 * 简历分析模块
 */

class ResumeModule {
  constructor() {
    this.results = [];
    this.careerProfiles = [];
  }

  init(container) {
    container.innerHTML = `
      <div class="resume-container">
        <div class="resume-header">
          <h1>简历分析</h1>
          <p>上传简历文件，AI 自动解析并提取关键信息</p>
        </div>

        <div class="career-db-panel">
          <div class="career-db-header">
            <div>
              <h3>职业画像库</h3>
              <p>HR 输入岗位要求后，AI 会统一整理并用于简历岗位推荐</p>
            </div>
            <span class="career-db-count" id="career-db-count">0 个岗位</span>
          </div>
          <textarea class="form-textarea career-db-input" id="career-requirement-input" placeholder="粘贴岗位职责、任职要求、加分项和成长期待"></textarea>
          <div class="career-db-actions">
            <button class="resume-btn primary" id="save-career-profile-btn">写入职业库</button>
          </div>
          <div class="career-profile-list" id="career-profile-list"></div>
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
            <p>支持 PDF、DOCX、图片型简历，最大 10MB</p>
            <input type="file" id="file-input" accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.bmp" style="display:none;">
          </div>
          <div class="upload-progress" id="upload-progress">
            <div class="progress-bar-bg"><div class="progress-bar-fill" id="progress-fill"></div></div>
            <div class="progress-text" id="progress-text">解析中...</div>
          </div>
        </div>

        <div class="parse-preview" id="parse-preview"></div>

        <div class="resume-results" id="resume-results"></div>
      </div>
    `;

    this._bindEvents(container);
    this._loadCareerProfiles(container);
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

    const saveCareerBtn = container.querySelector('#save-career-profile-btn');
    saveCareerBtn?.addEventListener('click', () => this._createCareerProfile(container));
  }

  async _createCareerProfile(container) {
    const input = container.querySelector('#career-requirement-input');
    const button = container.querySelector('#save-career-profile-btn');
    const text = input?.value.trim() || '';
    if (!text) {
      showToast('请先填写职业要求', 'error');
      return;
    }
    try {
      if (button) {
        button.disabled = true;
        button.textContent = '写入中...';
      }
      await api.createCareerProfile(text);
      if (input) input.value = '';
      showToast('职业画像已写入', 'success');
      await this._loadCareerProfiles(container);
    } catch (err) {
      showToast('职业画像写入失败: ' + err.message, 'error');
    } finally {
      if (button) {
        button.disabled = false;
        button.textContent = '写入职业库';
      }
    }
  }

  async _loadCareerProfiles(container) {
    const listEl = container.querySelector('#career-profile-list');
    const countEl = container.querySelector('#career-db-count');
    if (!listEl) return;
    try {
      const data = await api.listCareerProfiles();
      this.careerProfiles = data.profiles || [];
      if (countEl) countEl.textContent = `${this.careerProfiles.length} 个岗位`;
      if (this.careerProfiles.length === 0) {
        listEl.innerHTML = '<div class="career-profile-empty">暂无职业画像</div>';
        return;
      }
      listEl.innerHTML = this.careerProfiles.slice(0, 5).map(profile => `
        <div class="career-profile-card">
          <div class="career-profile-main">
            <div class="career-profile-title">${this._escape(profile.title || '未命名岗位')}</div>
            <div class="career-profile-meta">
              ${this._escape(profile.seniority || '不限')}
              ${(profile.skill_keywords || []).length ? ` · ${(profile.skill_keywords || []).slice(0, 5).map(s => this._escape(s)).join('、')}` : ''}
            </div>
          </div>
          <button class="resume-btn delete" onclick="window.resumeModule.deleteCareerProfile('${this._escapeAttr(profile.id)}')">删除</button>
        </div>
      `).join('');
    } catch (err) {
      listEl.innerHTML = '<div class="career-profile-empty">职业画像库加载失败</div>';
      console.error('加载职业画像库失败:', err);
    }
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

      if (result.status === 'failed') {
        throw new Error(result.error || '解析失败');
      }

      progressFill.style.width = '100%';
      progressText.textContent = '解析完成！';

      showToast(`简历 "${file.name}" 解析成功`, 'success');

      setTimeout(() => {
        progress.classList.remove('active');
        progressFill.style.width = '0%';
      }, 1500);

      this._loadResults(container);
      this._showParsePreview(result, container);
    } catch (err) {
      progressFill.style.width = '0%';
      progressText.textContent = '解析失败';
      showToast('简历解析失败: ' + err.message, 'error');
      setTimeout(() => progress.classList.remove('active'), 2000);
    }
  }

  _showParsePreview(result, container) {
    const previewEl = container.querySelector('#parse-preview');
    if (!previewEl) return;

    const parsed = result.parsed_data || {};
    const projects = parsed.project_experiences || [];
    const experiences = parsed.objective_experiences || [];
    const claims = parsed.claims || [];
    const formattedClaims = parsed.formatted_claims || [];
    const multidimensionalProfile = parsed.multidimensional_profile || {};
    const growthPotential = parsed.growth_potential || {};
    const roles = parsed.suitable_roles || [];
    const questions = parsed.interview_questions || [];
    const blindSpots = result.blind_spots || [];
    const footprint = parsed.digital_footprint || {};
    const name = parsed.name || result.source_filename || result.resume_id || '未知';

    previewEl.innerHTML = `
      <div class="parse-preview-card">
        <div class="parse-preview-header">
          <h3>${this._escape(name)} — 解析结果</h3>
          <button class="resume-btn" onclick="this.closest('.parse-preview-card').remove()">关闭</button>
        </div>

        ${this._renderMultidimensionalProfile(multidimensionalProfile)}

        ${this._renderGrowthPotential(growthPotential)}

        ${projects.length > 0 ? `
          <div class="parse-section">
            <h4>项目经历 (${projects.length})</h4>
            <div class="resume-project-grid">
              ${projects.map(p => this._renderProjectCard(p)).join('')}
            </div>
          </div>
        ` : this._renderExperienceFallback(experiences)}

        ${formattedClaims.length > 0 ? `
          <div class="parse-section">
            <h4>能力声明</h4>
            <div class="resume-claim-groups">
              ${formattedClaims.map(c => this._renderClaimGroup(c)).join('')}
            </div>
          </div>
        ` : this._renderRawClaims(claims)}

        ${roles.length > 0 ? `
          <div class="parse-section">
            <h4>适合投递岗位</h4>
            <div class="resume-role-grid">
              ${roles.map(r => this._renderRoleCard(r)).join('')}
            </div>
          </div>
        ` : ''}

        ${questions.length > 0 ? `
          <div class="parse-section">
            <h4>AI 面试辅助问题</h4>
            <div class="resume-question-list">
              ${questions.map(q => this._renderQuestion(q)).join('')}
            </div>
          </div>
        ` : ''}

        ${footprint.status === 'success' ? `
          <div class="parse-section">
            <h4>GitHub 数字足迹</h4>
            <div class="parse-item">
              <div>仓库: ${footprint.public_repos || 0} · Followers: ${footprint.followers || 0}</div>
              <div>主要语言: ${(footprint.top_languages || []).map(l => l[0]).join(', ') || '无'}</div>
              <div>活跃度: ${footprint.activity_signal || '-'}</div>
            </div>
            ${this._renderRepositoryPreviews(footprint.repository_previews || [])}
          </div>
        ` : ''}

        ${(footprint.blogs || []).length > 0 ? `
          <div class="parse-section">
            <h4>技术博客</h4>
            ${(footprint.blogs || []).map(b => `
              <div class="parse-item">
                <div class="parse-item-title">${this._escape(b.title || b.url || '')}</div>
                <div class="parse-item-desc">${this._escape((b.tags || []).join(', '))}</div>
              </div>
            `).join('')}
          </div>
        ` : ''}

        ${blindSpots.length > 0 ? `
          <div class="parse-section">
            <h4>信息盲区</h4>
            ${blindSpots.map(b => `<div class="parse-item parse-blind-spot">${this._escape(b)}</div>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
    previewEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
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
          const name = parsed.name || r.source_filename || r.resume_id || '未知';
          const projects = (parsed.project_experiences || []).length || (parsed.objective_experiences || []).length;
          const claims = (parsed.formatted_claims || []).length || (parsed.claims || []).length;
          const topRole = (parsed.suitable_roles || [])[0];
          const fitText = topRole?.fit_score ? ` · 最高契合 ${topRole.fit_score}%` : '';
          const roleSource = topRole?.source_label ? ` · ${this._escape(topRole.source_label)}` : '';
          const github = parsed.digital_footprint?.github_url || '';
          const candidateId = r.candidate_id ? ` · 候选人 ${this._escape(r.candidate_id)}` : '';
          return `
            <div class="resume-result-card" data-id="${r.resume_id}">
              <div class="resume-result-header">
                <span class="resume-result-title">${this._escape(name)}</span>
                <span class="resume-result-badge">${projects} 个项目 · ${claims} 类能力${fitText}</span>
              </div>
              <div class="resume-result-info">
                ${this._escape((parsed.project_experiences || []).slice(0, 2).map(p => p.name).join(' | ') || parsed.objective_experiences?.slice(0, 2).map(e => `${e.company} - ${e.title}`).join(' | ') || '暂无项目信息')}
                ${roleSource ? `<br>${roleSource}` : ''}
                ${github ? `<br>GitHub: ${this._escape(github)}` : ''}
                ${candidateId ? `<br>已同步到面试候选人库${candidateId}` : ''}
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
      const footprint = parsed.digital_footprint || {};

      const overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.innerHTML = `
        <div class="modal resume-detail-modal">
          <div class="modal-header">
            <div class="modal-title">简历详情 - ${this._escape(id)}</div>
          </div>
          <div class="resume-detail-content">
            ${this._renderMultidimensionalProfile(parsed.multidimensional_profile || {})}

            ${this._renderGrowthPotential(parsed.growth_potential || {})}

            ${this._renderDetailSection('项目经历', (parsed.project_experiences || []).map(p =>
              this._renderProjectCard(p)
            ).join('') || this._renderExperienceFallback(parsed.objective_experiences || []) || '<div class="resume-item">暂无</div>')}

            ${this._renderDetailSection('能力声明', (parsed.formatted_claims || []).map(c =>
              this._renderClaimGroup(c)
            ).join('') || this._renderRawClaims(parsed.claims || []) || '<div class="resume-item">暂无</div>')}

            ${this._renderDetailSection('适合投递岗位', (parsed.suitable_roles || []).map(r =>
              this._renderRoleCard(r)
            ).join('') || '<div class="resume-item">暂无</div>')}

            ${this._renderDetailSection('AI 面试辅助问题', (parsed.interview_questions || []).map(q =>
              this._renderQuestion(q)
            ).join('') || '<div class="resume-item">暂无</div>')}

            ${parsed.digital_footprint ? this._renderDetailSection('数字足迹', `
              <div class="resume-item">
                状态: ${this._escape(footprint.status || '无')}<br>
                GitHub: ${this._escape(footprint.github_url || '无')}<br>
                公开仓库: ${footprint.public_repos || 0}<br>
                Followers: ${footprint.followers || 0}<br>
                主要语言: ${(footprint.top_languages || []).map(l => l[0]).join(', ') || '无'}<br>
                最近仓库: ${(footprint.recent_repositories || []).map(r => r.name).filter(Boolean).slice(0, 5).join(', ') || '无'}<br>
                技术博客: ${(footprint.blogs || []).map(b => b.title || b.url).filter(Boolean).join(', ') || '无'}
              </div>
              ${this._renderRepositoryPreviews(footprint.repository_previews || [])}
            `) : ''}

            ${data.raw_text_preview ? this._renderDetailSection('原文预览',
              `<div class="resume-item resume-raw-preview">${this._escape(data.raw_text_preview)}</div>`
            ) : ''}

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

  _renderProjectCard(project) {
    const techStack = project.tech_stack || [];
    return `
      <div class="resume-project-card">
        <div class="resume-project-title">${this._escape(project.name || '未命名项目')}</div>
        ${project.summary ? `<div class="resume-project-summary">${this._escape(project.summary)}</div>` : ''}
        ${project.role ? `<div class="resume-project-meta">角色: ${this._escape(project.role)}</div>` : ''}
        ${project.impact ? `<div class="resume-project-impact">${this._escape(project.impact)}</div>` : ''}
        ${techStack.length > 0 ? `
          <div class="resume-tech-stack">
            ${techStack.map(t => `<span class="resume-tech-chip">${this._escape(t)}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  _renderExperienceFallback(experiences) {
    if (!experiences || experiences.length === 0) return '';
    return `
      <div class="parse-section">
        <h4>客观经历 (${experiences.length})</h4>
        ${experiences.map(e => `
          <div class="parse-item">
            <div class="parse-item-title">${this._escape(e.company || '经历')} ${e.title ? `— ${this._escape(e.title)}` : ''}</div>
            <div class="parse-item-desc">${this._escape(this._truncate(e.description || '', 160))}</div>
            <div class="parse-item-meta">信号强度: ${e.signal_strength || '-'} / 5 · STAR 完整度: ${e.star_completeness || '-'}</div>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderClaimGroup(claim) {
    return `
      <div class="resume-claim-group">
        <div class="resume-claim-head">
          <span>${this._escape(claim.category || '综合能力')}</span>
          <span class="resume-score">信号 ${claim.signal_strength || '-'}/5</span>
        </div>
        <div class="resume-claim-items">
          ${(claim.items || []).map(item => `<span>${this._escape(item)}</span>`).join('')}
        </div>
        ${claim.evidence ? `<div class="resume-claim-evidence">${this._escape(claim.evidence)}</div>` : ''}
      </div>
    `;
  }

  _renderRawClaims(claims) {
    if (!claims || claims.length === 0) return '';
    return `
      <div class="parse-section">
        <h4>能力声明 (${claims.length})</h4>
        ${claims.map(c => `
          <div class="parse-item">
            <span class="parse-claim-text">${this._escape(c.content || '')}</span>
            <span class="parse-claim-strength">信号强度: ${c.signal_strength || '-'} / 5</span>
          </div>
        `).join('')}
      </div>
    `;
  }

  _renderRoleCard(role) {
    const fitScore = this._clampPercent(role.fit_score ?? 0);
    const growthFitScore = this._clampPercent(role.growth_fit_score ?? fitScore);
    return `
      <div class="resume-role-card">
        <div class="resume-role-head">
          <div class="resume-role-title">${this._escape(role.title || '')}</div>
          ${role.fit_score !== undefined ? `<div class="resume-fit-score">${fitScore}%</div>` : ''}
        </div>
        ${role.source_label ? `<div class="resume-role-source ${role.in_career_database ? 'in-db' : 'out-db'}">${this._escape(role.source_label)}</div>` : ''}
        ${role.fit_score !== undefined ? `
          <div class="resume-fit-meter" aria-label="岗位契合度 ${fitScore}%">
            <div class="resume-fit-fill" style="width:${fitScore}%"></div>
          </div>
        ` : ''}
        <div class="resume-role-reason">${this._escape(role.reason || '')}</div>
        ${role.fit_reason ? `<div class="resume-role-fit-reason">${this._escape(role.fit_reason)}</div>` : ''}
        ${role.growth_fit_score !== undefined ? `
          <div class="resume-growth-fit">
            <span>成长适配 ${growthFitScore}%</span>
            ${role.growth_fit_reason ? `<em>${this._escape(role.growth_fit_reason)}</em>` : ''}
          </div>
        ` : ''}
        ${(role.matching_skills || []).length > 0 ? `
          <div class="resume-tech-stack">
            ${role.matching_skills.map(s => `<span class="resume-tech-chip">${this._escape(s)}</span>`).join('')}
          </div>
        ` : ''}
        ${role.risk ? `<div class="resume-role-risk">${this._escape(role.risk)}</div>` : ''}
      </div>
    `;
  }

  _renderMultidimensionalProfile(profile) {
    const dimensions = profile?.dimensions || [];
    if (!dimensions.length) return '';
    return `
      <div class="parse-section resume-profile-section">
        <h4>多维职业画像</h4>
        ${(profile.overall_tags || []).length > 0 ? `
          <div class="resume-profile-tags">
            ${profile.overall_tags.map(tag => `<span>${this._escape(tag)}</span>`).join('')}
          </div>
        ` : ''}
        ${profile.summary ? `<div class="resume-profile-summary">${this._escape(profile.summary)}</div>` : ''}
        <div class="resume-dimension-list">
          ${dimensions.map(dim => this._renderDimensionAxis(dim)).join('')}
        </div>
      </div>
    `;
  }

  _renderGrowthPotential(growth) {
    if (!growth || !growth.score) return '';
    const score = this._clampPercent(growth.score);
    const dimensions = growth.dimensions || [];
    return `
      <div class="parse-section resume-growth-section">
        <div class="resume-growth-head">
          <h4>成长性推理</h4>
          <span class="resume-growth-score">${score}% · ${this._escape(growth.level || '-')}</span>
        </div>
        ${growth.summary ? `<div class="resume-profile-summary">${this._escape(growth.summary)}</div>` : ''}
        ${(growth.evidence || []).length > 0 ? `
          <div class="resume-growth-evidence">
            ${(growth.evidence || []).map(item => `<span>${this._escape(item)}</span>`).join('')}
          </div>
        ` : ''}
        ${dimensions.length > 0 ? `
          <div class="resume-growth-dimensions">
            ${dimensions.map(dim => `
              <div class="resume-growth-dimension">
                <div class="resume-growth-dimension-head">
                  <span>${this._escape(dim.name || '')}</span>
                  <strong>${this._clampPercent(dim.score ?? 0)}%</strong>
                </div>
                ${dim.summary ? `<div>${this._escape(dim.summary)}</div>` : ''}
              </div>
            `).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  _renderDimensionAxis(dim) {
    const score = this._clampPercent(dim.score ?? 50);
    return `
      <div class="resume-dimension">
        <div class="resume-dimension-head">
          <span>${this._escape(dim.left_label || '')}</span>
          <span>${this._escape(dim.right_label || '')}</span>
        </div>
        <div class="resume-axis">
          <div class="resume-axis-mid"></div>
          <div class="resume-axis-marker" style="left:${score}%"></div>
        </div>
        <div class="resume-dimension-meta">
          <span>${this._escape(dim.summary || '')}</span>
          <span>置信 ${this._escape(dim.confidence || '-')}/5</span>
        </div>
        ${dim.evidence ? `<div class="resume-dimension-evidence">${this._escape(dim.evidence)}</div>` : ''}
      </div>
    `;
  }

  _renderQuestion(question) {
    const difficultyText = { easy: '基础', medium: '中等', hard: '深入' }[question.difficulty] || '中等';
    return `
      <div class="resume-question">
        <div class="resume-question-main">${this._escape(question.question || '')}</div>
        <div class="resume-question-meta">${difficultyText}${question.purpose ? ` · ${this._escape(question.purpose)}` : ''}${question.based_on ? ` · ${this._escape(question.based_on)}` : ''}</div>
      </div>
    `;
  }

  _renderRepositoryPreviews(previews) {
    if (!previews || previews.length === 0) return '';
    return `
      <div class="repo-preview-grid">
        ${previews.map(repo => `
          <a class="repo-preview-card" href="${this._escapeAttr(repo.url || '#')}" target="_blank" rel="noopener noreferrer">
            ${repo.preview_image ? `<img src="${this._escapeAttr(repo.preview_image)}" alt="${this._escapeAttr(repo.name || 'repo')}">` : ''}
            <div class="repo-preview-body">
              <div class="repo-preview-title">${this._escape(repo.name || '')}</div>
              <div class="repo-preview-summary">${this._escape(repo.summary || repo.readme_excerpt || '暂无项目描述')}</div>
              <div class="repo-preview-meta">★ ${repo.stars || 0} · Fork ${repo.forks || 0}${repo.updated_at ? ` · ${this._escape(repo.updated_at.slice(0, 10))}` : ''}</div>
              ${(repo.tech_stack || []).length > 0 ? `
                <div class="resume-tech-stack">
                  ${repo.tech_stack.map(t => `<span class="resume-tech-chip">${this._escape(t)}</span>`).join('')}
                </div>
              ` : ''}
            </div>
          </a>
        `).join('')}
      </div>
    `;
  }

  async deleteResult(id) {
    if (!confirm('确定删除此简历解析结果？')) return;
    try {
      await api.deleteResumeResult(id);
      showToast('删除成功', 'success');
      const container = document.querySelector('.resume-container');
      if (container) this._loadResults(container);
    } catch (err) {
      showToast('删除失败: ' + err.message, 'error');
    }
  }

  async deleteCareerProfile(id) {
    if (!confirm('确定删除此职业画像？')) return;
    try {
      await api.deleteCareerProfile(id);
      showToast('职业画像已删除', 'success');
      const container = document.querySelector('.resume-container');
      if (container) this._loadCareerProfiles(container);
    } catch (err) {
      showToast('删除失败: ' + err.message, 'error');
    }
  }

  _escape(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  _escapeAttr(text) {
    return this._escape(text).replace(/"/g, '&quot;');
  }

  _truncate(text, maxLength) {
    if (!text || text.length <= maxLength) return text || '';
    return text.slice(0, maxLength - 1) + '…';
  }

  _clampPercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return 0;
    return Math.max(0, Math.min(100, Math.round(number)));
  }
}

window.resumeModule = new ResumeModule();
