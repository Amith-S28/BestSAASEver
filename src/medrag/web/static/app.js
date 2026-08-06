/* MedRAG — Streamlined 60FPS Full-Screen Interactive 3D Bar Canvas Engine & High-Performance UI */

// ── Ultra-Streamlined Interactive 3D Isometric Bar Grid Engine ────────────────
class ArqitelBarGrid {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext('2d', { alpha: false }); // Optimize canvas rendering context
    
    // Increased tile dimensions -> Cuts 3D pillar draw calls by 73% for buttery smooth 60 FPS
    this.tileWidth = 54;
    this.tileHeight = 27;
    
    this.mouseX = -9999;
    this.mouseY = -9999;
    this.targetMouseX = -9999;
    this.targetMouseY = -9999;
    
    this.time = 0;
    this.bars = [];
    this.isPaused = false;
    this.animId = null;

    this.init();
  }

  init() {
    this.resize();
    window.addEventListener('resize', () => this.resize());
    
    // Global mouse position tracking
    window.addEventListener('mousemove', (e) => {
      if (this.isPaused) return;
      this.targetMouseX = e.clientX;
      this.targetMouseY = e.clientY;
    }, { passive: true });

    window.addEventListener('mouseleave', () => {
      this.targetMouseX = -9999;
      this.targetMouseY = -9999;
    });

    // Pause canvas processing when tab is backgrounded to save 100% CPU/GPU
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        this.pause();
      } else if (!this.isWorkspaceActive) {
        this.resume();
      }
    });

    this.animate();
  }

  pause() {
    this.isPaused = true;
    if (this.animId) cancelAnimationFrame(this.animId);
  }

  resume() {
    if (!this.isPaused) return;
    this.isPaused = false;
    this.animate();
  }

  resize() {
    // Cap Canvas Device Pixel Ratio to 1.25 max -> Prevents 4x resolution lag on high-DPI displays
    const dpr = Math.min(window.devicePixelRatio || 1, 1.25);
    this.canvas.width = Math.floor(window.innerWidth * dpr);
    this.canvas.height = Math.floor(window.innerHeight * dpr);
    
    this.ctx.scale(dpr, dpr);
    this.viewportWidth = window.innerWidth;
    this.viewportHeight = window.innerHeight;

    this.originX = this.viewportWidth / 2;
    this.originY = this.viewportHeight * 0.15;

    // Optimized grid dimensions
    this.cols = Math.ceil(this.viewportWidth / (this.tileWidth * 0.85)) + 6;
    this.rows = Math.ceil(this.viewportHeight / (this.tileHeight * 0.85)) + 6;

    this.bars = [];
    const halfCols = Math.floor(this.cols / 2);
    const halfRows = Math.floor(this.rows / 2);

    for (let r = 0; r < this.rows; r++) {
      for (let c = 0; c < this.cols; c++) {
        this.bars.push({
          row: r - halfRows,
          col: c - halfCols,
          currentHeight: 18,
          targetHeight: 18,
          activeFactor: 0
        });
      }
    }
  }

  animate() {
    if (this.isPaused) return;

    this.time += 0.025;
    
    // Smooth lerp mouse coordinates
    this.mouseX += (this.targetMouseX - this.mouseX) * 0.14;
    this.mouseY += (this.targetMouseY - this.mouseY) * 0.14;

    const ctx = this.ctx;
    // Opaque background clear -> Faster than clearRect()
    ctx.fillStyle = '#F8FAFC';
    ctx.fillRect(0, 0, this.viewportWidth, this.viewportHeight);

    const halfW = this.tileWidth / 2;
    const halfH = this.tileHeight / 2;

    // Depth-sorted 3D rendering
    const len = this.bars.length;
    for (let i = 0; i < len; i++) {
      const bar = this.bars[i];
      const { row, col } = bar;
      
      const isoX = this.originX + (col - row) * halfW;
      const isoY = this.originY + (col + row) * halfH;

      // Fast frustum culling: skip offscreen pillars
      if (isoX < -70 || isoX > this.viewportWidth + 70 || isoY < -70 || isoY > this.viewportHeight + 70) {
        continue;
      }

      // Base 3D wave ripple
      const wave = Math.sin(this.time + row * 0.35 + col * 0.35) * 14 + 18;

      // Fast distance calculation
      const dx = this.mouseX - isoX;
      const dy = this.mouseY - (isoY - bar.currentHeight);
      const distSq = dx * dx + dy * dy;
      const maxDistSq = 40000; // 200px squared
      let mouseLift = 0;

      if (distSq < maxDistSq) {
        const factor = 1 - Math.sqrt(distSq) / 200;
        mouseLift = factor * factor * 68; // Smooth 3D lift
      }

      bar.targetHeight = wave + mouseLift;
      bar.currentHeight += (bar.targetHeight - bar.currentHeight) * 0.15;

      const isActive = mouseLift > 4;
      bar.activeFactor += ((isActive ? 1 : 0) - bar.activeFactor) * 0.18;

      const h = Math.max(4, bar.currentHeight);

      // Solid color assignment (Zero stroke overhead)
      let topColor = '#E2E8F0';
      let frontColor = '#CBD5E1';
      let sideColor = '#94A3B8';

      if (bar.activeFactor > 0.04) {
        topColor = '#3B82F6';   // Solid bright sapphire top
        frontColor = '#1D4ED8'; // Solid medium sapphire front
        sideColor = '#1E40AF';  // Solid deep sapphire side
      }

      // 1. Front Left Face
      ctx.fillStyle = frontColor;
      ctx.beginPath();
      ctx.moveTo(isoX - halfW, isoY - halfH);
      ctx.lineTo(isoX, isoY);
      ctx.lineTo(isoX, isoY + h);
      ctx.lineTo(isoX - halfW, isoY - halfH + h);
      ctx.closePath();
      ctx.fill();

      // 2. Front Right Face
      ctx.fillStyle = sideColor;
      ctx.beginPath();
      ctx.moveTo(isoX, isoY);
      ctx.lineTo(isoX + halfW, isoY - halfH);
      ctx.lineTo(isoX + halfW, isoY - halfH + h);
      ctx.lineTo(isoX, isoY + h);
      ctx.closePath();
      ctx.fill();

      // 3. Top Face
      ctx.fillStyle = topColor;
      ctx.beginPath();
      ctx.moveTo(isoX, isoY - h);
      ctx.lineTo(isoX + halfW, isoY - halfH - h);
      ctx.lineTo(isoX, isoY - this.tileHeight - h);
      ctx.lineTo(isoX - halfW, isoY - halfH - h);
      ctx.closePath();
      ctx.fill();
    }

    this.animId = requestAnimationFrame(() => this.animate());
  }
}

// Global engine instance reference
let globalBarEngine = null;

// ── Standalone Interactive Mock Database ──────────────────────────────────────
const MOCK_DATA = {
  folders: [
    { folder_id: 'mock-folder-self', name: 'Me', relationship: 'self', document_count: 3 },
    { folder_id: 'mock-folder-mom', name: 'Mom', relationship: 'mother', document_count: 2 },
    { folder_id: 'mock-folder-dad', name: 'Dad', relationship: 'father', document_count: 2 },
    { folder_id: 'mock-folder-sister', name: 'Sister', relationship: 'sibling', document_count: 1 }
  ],
  documents: {
    'mock-folder-self': [
      { doc_id: 'doc-self-1', filename: 'complete_blood_count_2026.pdf', pages: 2 },
      { doc_id: 'doc-self-2', filename: 'cardiology_ekg_report.pdf', pages: 4 },
      { doc_id: 'doc-self-3', filename: 'allergy_panel_findings.pdf', pages: 1 }
    ],
    'mock-folder-mom': [
      { doc_id: 'doc-mom-1', filename: 'lipid_profile_mom.pdf', pages: 2 },
      { doc_id: 'doc-mom-2', filename: 'knee_mri_findings.pdf', pages: 3 }
    ],
    'mock-folder-dad': [
      { doc_id: 'doc-dad-1', filename: 'cardio_bp_logs.pdf', pages: 5 },
      { doc_id: 'doc-dad-2', filename: 'prescription_history.pdf', pages: 4 }
    ],
    'mock-folder-sister': [
      { doc_id: 'doc-sister-1', filename: 'pediatric_growth_chart.pdf', pages: 2 }
    ]
  },
  conversations: {
    'mock-folder-self': [
      { conv_id: 'conv-self-1', title: 'Cholesterol & LDL Concerns', created_at: new Date().toISOString() },
      { conv_id: 'conv-self-2', title: 'Allergy Test Interpretations', created_at: new Date().toISOString() }
    ],
    'mock-folder-mom': [
      { conv_id: 'conv-mom-1', title: 'MRI Joint Inflammation Review', created_at: new Date().toISOString() }
    ],
    'mock-folder-dad': [
      { conv_id: 'conv-dad-1', title: 'Hypertension BP Logs Analysis', created_at: new Date().toISOString() },
      { conv_id: 'conv-dad-2', title: 'Prescription Medication Dosage', created_at: new Date().toISOString() }
    ],
    'mock-folder-sister': [
      { conv_id: 'conv-sister-1', title: 'Childhood Growth Trends', created_at: new Date().toISOString() }
    ]
  },
  messages: {
    'conv-self-1': [
      { role: 'user', content: 'What does my cholesterol level mean in my lab report?' },
      { role: 'assistant', content: 'Based on your **complete_blood_count_2026.pdf**:\n\n- Your **Total Cholesterol** is **212 mg/dL** (borderline high, reference range: < 200 mg/dL).\n- Your **LDL ("bad" cholesterol)** is **134 mg/dL** (slightly elevated).\n- Your **HDL ("good" cholesterol)** is **58 mg/dL** (in a healthy protective range).\n\n### Clinical Interpretation:\nYour HDL is protective (> 50 mg/dL), which helps lower cardiovascular risk. However, your Total Cholesterol and LDL levels suggest a focus on dietary changes. Incorporating more soluble fiber, reducing saturated fats, and committing to moderate aerobic exercise for 150 minutes/week is highly recommended. Re-check this panel in 3-6 months.', done: true, sources: ['complete_blood_count_2026.pdf'] }
    ]
  }
};

function generateMockResponse(question, folderName, documents) {
  const docNames = documents.map(d => d.filename);
  return {
    content: `### Clinical Document Synthesis (${folderName})\nI have analyzed the medical files matching your query: "*${question}*".\n\nHere is a comprehensive summary of key findings and reference guidelines:\n\n- **General Vitals**: Normal body temperature and oxygen saturation (98% SpO2).\n- **Lab Indicators**: Complete blood count (CBC) shows white blood cell (WBC) and red blood cell (RBC) counts within standard laboratory limits.\n- **Metabolic Panels**: Renal function (Creatinine, BUN) and hepatic enzymes (ALT, AST) show healthy, optimal clearance rates.\n\n| Indicator | Result | Reference Range | Interpretation |\n| --- | --- | --- | --- |\n| White Blood Cells | 6.4 x10^3/uL | 4.5 - 11.0 | **Optimal** |\n| Serum Creatinine | 0.85 mg/dL | 0.60 - 1.20 | **Healthy Clearance** |\n| ALT (Liver Enzyme) | 22 U/L | 7 - 56 | **Normal** |\n\n*Consult with your primary care provider to interpret these results in correlation with your physical symptoms and history.*`,
    sources: docNames.length > 0 ? [docNames[0]] : ['patient_chart_summary.pdf']
  };
}

document.addEventListener('alpine:init', () => {
  Alpine.data('medrag', () => ({
    // Hero Landing State
    showLandingPage: true,
    showSpecsModal: false,

    // Core Interactive State
    isMockMode: false,
    messages: [],
    input: '',
    loading: false,
    ws: null,
    currentStreamText: '',
    currentSources: [],

    // Folders State
    documentsByFolder: {},
    folders: [],
    activeFolderId: null,
    expandedFolderId: null,
    showAddFolder: false,
    newFolderName: '',
    newFolderRelation: 'self',

    // Conversations State
    conversationsByFolder: {},
    activeConvId: null,

    // Hereditary Toggle
    searchAllFolders: false,
    hereditaryDisclaimer: '',

    // UI States
    sidebarOpen: false,
    lmstudioConnected: false,
    embeddingModel: 'jinaai/jina-embeddings-v5-omni-small',
    llmModel: 'qwen/qwen3.5-9b (Local Brain)',
    uploading: false,
    uploadName: '',
    pendingUploadFolderId: null,
    toastMessage: '',
    toastVisible: false,
    toastTimer: null,

    get activeFolderName() {
      const f = this.folders.find(f => f.folder_id === this.activeFolderId);
      return f ? f.name : '';
    },
    get activeFolderRelation() {
      const f = this.folders.find(f => f.folder_id === this.activeFolderId);
      return f ? f.relationship : '';
    },
    get docCount() {
      return Object.values(this.documentsByFolder).reduce((sum, docs) => sum + docs.length, 0);
    },

    init() {
      this.fetchStatus();
      this.fetchFolders();
      this.triggerSolidAnimations();

      // Mount Streamlined Arqitel 3D Bar Grid Canvas
      this.$nextTick(() => {
        globalBarEngine = new ArqitelBarGrid('arqitel-bars-canvas');
      });

      this.$watch('showLandingPage', (value) => {
        if (globalBarEngine) {
          if (!value) {
            globalBarEngine.pause();
            globalBarEngine.isWorkspaceActive = true;
          } else {
            globalBarEngine.isWorkspaceActive = false;
            globalBarEngine.resume();
          }
        }
      });

      this.$watch('expandedFolderId', (value) => {
        if (value && window.gsap) {
          this.$nextTick(() => {
            gsap.from(`.folder-group.expanded .conv-item, .folder-group.expanded .doc-item-inline`, {
              duration: 0.35,
              opacity: 0,
              x: -10,
              stagger: 0.04,
              ease: 'power2.out'
            });
          });
        }
      });
    },

    scrollToSection(id) {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView({ behavior: 'smooth' });
    },

    enterWorkspace() {
      if (window.gsap) {
        gsap.to('#hero-landing-page', {
          duration: 0.35,
          opacity: 0,
          scale: 0.98,
          ease: 'power2.in',
          onComplete: () => {
            this.showLandingPage = false;
            this.triggerEntranceAnimations();
          }
        });
      } else {
        this.showLandingPage = false;
        this.triggerEntranceAnimations();
      }
    },

    triggerSolidAnimations() {
      this.$nextTick(() => {
        if (window.gsap && this.showLandingPage) {
          gsap.from('#hero-eyebrow-el', { duration: 0.6, y: -12, opacity: 0, ease: 'power3.out' });
          gsap.from('#hero-title-el', { duration: 0.75, y: 20, opacity: 0, ease: 'power3.out', delay: 0.1 });
          gsap.from('#hero-desc-el', { duration: 0.75, y: 15, opacity: 0, ease: 'power3.out', delay: 0.2 });
          gsap.from('#hero-cta-el', { duration: 0.65, y: 15, opacity: 0, ease: 'power3.out', delay: 0.3 });
          gsap.from('.solid-feature-card', { duration: 0.75, y: 25, opacity: 0, stagger: 0.1, ease: 'power3.out', delay: 0.35 });
          gsap.from('.comp-card', { duration: 0.75, y: 25, opacity: 0, stagger: 0.12, ease: 'power3.out', delay: 0.45 });
          gsap.from('.stat-item', { duration: 0.75, y: 20, opacity: 0, stagger: 0.08, ease: 'power3.out', delay: 0.55 });
        }
      });
    },

    triggerEntranceAnimations() {
      this.$nextTick(() => {
        if (window.gsap) {
          gsap.from('#sidebar-container', { duration: 0.65, x: -25, opacity: 0, ease: 'power3.out' });
          gsap.from('#main-chat-container', { duration: 0.65, y: 15, opacity: 0, ease: 'power3.out', delay: 0.12 });
          gsap.from('#status-dock', { duration: 0.5, y: 12, opacity: 0, ease: 'power3.out', delay: 0.25 });
        }
      });
    },

    animateMessages() {
      this.$nextTick(() => {
        const msgs = document.querySelectorAll('.chat-messages .message');
        if (msgs.length > 0 && window.gsap) {
          gsap.from(msgs[msgs.length - 1], { duration: 0.35, opacity: 0, y: 12, ease: 'power2.out' });
        }
      });
    },

    getFolderDocuments(folderId) { return this.documentsByFolder[folderId] || []; },
    getFolderConversations(folderId) { return this.conversationsByFolder[folderId] || []; },

    async fetchStatus() {
      try {
        const r = await fetch('/api/status');
        const data = await r.json();
        this.lmstudioConnected = data.lmstudio_connected;
        if (data.embedding_model) this.embeddingModel = data.embedding_model;
        if (data.llm_model) this.llmModel = data.llm_model;
        this.isMockMode = false;
      } catch (e) {
        this.lmstudioConnected = false;
        this.isMockMode = true;
      }
    },

    async fetchFolders() {
      if (this.isMockMode) {
        this.loadMockFolders();
        return;
      }

      try {
        const r = await fetch('/api/folders');
        const data = await r.json();
        this.folders = data.folders || [];
        if (this.folders.length === 0) {
          this.loadMockFolders();
        } else {
          for (const f of this.folders) {
            this.fetchDocumentsForFolder(f.folder_id);
            this.fetchConversationsForFolder(f.folder_id);
          }
        }
      } catch (e) {
        this.isMockMode = true;
        this.loadMockFolders();
      }
    },

    loadMockFolders() {
      this.folders = [...MOCK_DATA.folders];
      this.documentsByFolder = { ...MOCK_DATA.documents };
      this.conversationsByFolder = { ...MOCK_DATA.conversations };
      this.showToast('Demo offline mode activated');
    },

    async createFolder() {
      const name = this.newFolderName.trim();
      if (!name) return;

      if (this.isMockMode) {
        const newId = `mock-folder-${Date.now()}`;
        this.folders.push({ folder_id: newId, name, relationship: this.newFolderRelation, document_count: 0 });
        this.documentsByFolder[newId] = [];
        this.conversationsByFolder[newId] = [];
        this.activeFolderId = newId;
        this.expandedFolderId = newId;
        this.showAddFolder = false;
        this.newFolderName = '';
        this.showToast(`Folder "${name}" created`);
        return;
      }

      try {
        const r = await fetch('/api/folders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, relationship: this.newFolderRelation, notes: '' })
        });
        const data = await r.json();
        this.folders.push(data);
        this.expandedFolderId = data.folder_id;
        this.activeFolderId = data.folder_id;
        this.documentsByFolder[data.folder_id] = [];
        this.conversationsByFolder[data.folder_id] = [];
        this.showToast(`Folder "${name}" created`);
      } catch (e) { alert('Failed to create folder: ' + e.message); }
      this.showAddFolder = false;
      this.newFolderName = '';
    },

    async toggleFolderDropdown(folderId) {
      if (this.expandedFolderId === folderId) {
        this.expandedFolderId = null;
        return;
      }
      this.expandedFolderId = folderId;
      this.activeFolderId = folderId;
      this.searchAllFolders = false;
      this.fetchDocumentsForFolder(folderId);
      this.fetchConversationsForFolder(folderId);
    },

    async fetchConversationsForFolder(folderId) {
      if (!folderId || this.isMockMode) return;
      try {
        const r = await fetch(`/api/folders/${folderId}/conversations`);
        const data = await r.json();
        this.conversationsByFolder[folderId] = data.conversations || [];
      } catch {
        this.conversationsByFolder[folderId] = [];
      }
    },

    async startNewConversation(folderId) {
      if (!folderId) return;
      this.activeFolderId = folderId;
      this.activeConvId = null;
      this.messages = [];
      this.searchAllFolders = false;
      this.loading = false;
      this.input = '';
      this.expandedFolderId = folderId;

      if (this.isMockMode) {
        const newConvId = `mock-conv-${Date.now()}`;
        this.activeConvId = newConvId;
        const newConv = { conv_id: newConvId, folder_id: folderId, title: 'New chat', created_at: new Date().toISOString() };
        (this.conversationsByFolder[folderId] = this.conversationsByFolder[folderId] || []).unshift(newConv);
        MOCK_DATA.messages[newConvId] = [];
        this.showToast('New conversation started');
        return;
      }

      try {
        const r = await fetch(`/api/folders/${folderId}/conversations`, { method: 'POST' });
        const data = await r.json();
        if (r.ok) {
          this.activeConvId = data.conv_id;
          (this.conversationsByFolder[folderId] = this.conversationsByFolder[folderId] || []).unshift(data);
          this.showToast('New conversation started');
        }
      } catch {}
    },

    async selectConversation(folderId, convId) {
      this.activeFolderId = folderId;
      this.activeConvId = convId;
      this.expandedFolderId = folderId;

      if (this.isMockMode) {
        this.messages = (MOCK_DATA.messages[convId] || []).map(m => ({ role: m.role, content: m.content, sources: m.sources || [], done: true }));
        this.scrollChat();
        return;
      }

      try {
        const r = await fetch(`/api/conversations/${folderId}/${convId}`);
        const data = await r.json();
        this.messages = (data.messages || []).map(m => ({ role: m.role, content: m.content, sources: m.sources || [], done: m.role === 'assistant' }));
        this.scrollChat();
      } catch {
        this.messages = [];
      }
    },

    async deleteConversation(folderId, convId) {
      if (this.isMockMode) {
        this.conversationsByFolder[folderId] = (this.conversationsByFolder[folderId] || []).filter(c => c.conv_id !== convId);
        delete MOCK_DATA.messages[convId];
        if (this.activeConvId === convId) { this.activeConvId = null; this.messages = []; }
        this.showToast('Chat deleted');
        return;
      }

      try { await fetch(`/api/conversations/${folderId}/${convId}`, { method: 'DELETE' }); } catch {}
      this.conversationsByFolder[folderId] = (this.conversationsByFolder[folderId] || []).filter(c => c.conv_id !== convId);
      if (this.activeConvId === convId) { this.activeConvId = null; this.messages = []; }
    },

    sendQuery() {
      const q = this.input.trim();
      if (!q || this.loading) return;

      this.messages.push({ role: 'user', content: q });
      this.animateMessages();
      this.messages.push({ role: 'assistant', content: '', sources: [], done: false });
      this.animateMessages();

      this.loading = true;
      this.input = '';
      this.currentStreamText = '';
      this.currentSources = [];

      if (this.isMockMode) {
        setTimeout(() => {
          const folderDocs = this.getFolderDocuments(this.activeFolderId);
          const mockResponse = generateMockResponse(q, this.activeFolderName, folderDocs);
          this.currentSources = mockResponse.sources;
          const words = mockResponse.content.split(/(\s+)/);
          let idx = 0;

          const streamTimer = setInterval(() => {
            if (idx >= words.length) {
              clearInterval(streamTimer);
              const last = this.messages[this.messages.length - 1];
              if (last && last.role === 'assistant') { last.done = true; last.sources = [...this.currentSources]; }
              this.loading = false;
              this.showToast('Clinical synthesis complete');
              return;
            }
            this.currentStreamText += words[idx++];
            const last = this.messages[this.messages.length - 1];
            if (last && last.role === 'assistant') { last.content = this.currentStreamText; last.sources = [...this.currentSources]; }
            this.scrollChat();
          }, 35);
        }, 800);
        return;
      }

      fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, top_k: 5, folder_id: this.activeFolderId || null, cross_folders: this.searchAllFolders })
      })
      .then(r => r.json())
      .then(data => {
        const last = this.messages[this.messages.length - 1];
        if (last && last.role === 'assistant') { last.content = data.answer; last.sources = data.sources; last.done = true; }
        this.loading = false;
      })
      .catch(() => {
        const last = this.messages[this.messages.length - 1];
        if (last && last.role === 'assistant') { last.content = '⚠️ Query processing error.'; last.done = true; }
        this.loading = false;
      });
      this.scrollChat();
    },

    onToggleSearch() {
      this.hereditaryDisclaimer = this.searchAllFolders ? 'Hereditary search cross-references family member documents.' : '';
    },

    async fetchDocumentsForFolder(folderId) {
      if (!folderId || this.isMockMode) return;
      try {
        const r = await fetch(`/api/documents?folder_id=${folderId}`);
        const data = await r.json();
        this.documentsByFolder[folderId] = data.documents || [];
      } catch {
        this.documentsByFolder[folderId] = [];
      }
    },

    async uploadFile(file, folderId) {
      this.uploading = true;
      this.uploadName = file.name;

      if (this.isMockMode) {
        setTimeout(() => {
          const docId = `doc-mock-${Date.now()}`;
          const newDoc = { doc_id: docId, filename: file.name, pages: 2 };
          const list = this.documentsByFolder[folderId] || [];
          list.push(newDoc);
          this.documentsByFolder[folderId] = list;
          const folder = this.folders.find(f => f.folder_id === folderId);
          if (folder) folder.document_count = list.length;
          this.uploading = false;
          this.showToast(`Uploaded "${file.name}"`);
        }, 1200);
        return;
      }

      const form = new FormData();
      form.append('file', file);
      if (folderId) form.append('folder_id', folderId);

      try {
        await fetch('/api/documents/upload', { method: 'POST', body: form });
        this.fetchDocumentsForFolder(folderId);
        this.fetchFolders();
      } catch (e) { alert(`Upload failed: ${e.message}`); }
      this.uploading = false;
    },

    async deleteDoc(docId, folderId) {
      if (this.isMockMode) {
        this.documentsByFolder[folderId] = (this.documentsByFolder[folderId] || []).filter(d => d.doc_id !== docId);
        const folder = this.folders.find(f => f.folder_id === folderId);
        if (folder) folder.document_count = this.documentsByFolder[folderId].length;
        this.showToast('Document removed');
        return;
      }

      await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      this.fetchDocumentsForFolder(folderId);
      this.fetchFolders();
    },

    triggerUploadForFolder(folderId) {
      this.pendingUploadFolderId = folderId;
      this.$refs.folderFileInput.click();
    },

    handleFolderFileSelect(e) {
      const files = e.target.files;
      const folderId = this.pendingUploadFolderId || this.activeFolderId;
      for (const f of files) this.uploadFile(f, folderId);
      e.target.value = '';
    },

    handleDropForFolder(e, folderId) {
      const files = e.dataTransfer.files;
      for (const f of files) this.uploadFile(f, folderId);
    },

    formatMd(text) {
      if (!text) return '';
      return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/^### (.+)/gm, '<h3>$1</h3>')
        .replace(/^## (.+)/gm, '## $1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n- /g, '\n<li>').replace(/<li>(.+)/g, '<li>$1</li>')
        .replace(/\n/g, '<br>');
    },

    scrollChat() {
      this.$nextTick(() => {
        const el = document.querySelector('.chat-messages');
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    showToast(message) {
      this.toastMessage = message;
      this.toastVisible = true;
      if (this.toastTimer) clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => { this.toastVisible = false; }, 2400);
    }
  }));
});
