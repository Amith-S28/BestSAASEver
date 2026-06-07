/* MedRAG Frontend — Alpine.js app with family folder dropdowns + chat history */

document.addEventListener('alpine:init', () => {
  Alpine.data('medrag', () => ({
    // Chat
    messages: [],
    input: '',
    loading: false,
    ws: null,
    currentStreamText: '',
    currentSources: [],

    // Documents — indexed by folder_id
    documentsByFolder: {},

    // Status
    lmstudioConnected: false,
    docCount: 0,
    embeddingModel: '',
    llmModel: '',

    // Upload
    uploading: false,
    uploadName: '',
    pendingUploadFolderId: null,

    // Folders
    folders: [],
    activeFolderId: null,
    expandedFolderId: null,
    showAddFolder: false,
    newFolderName: '',
    newFolderRelation: 'self',

    // Conversations — indexed by folder_id
    conversationsByFolder: {},
    activeConvId: null,

    // Hereditary search
    searchAllFolders: false,
    hereditaryDisclaimer: '',

    // Mobile sidebar
    sidebarOpen: false,

    // Computed
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
      this.connectWs();
      this.fetchStatus();
      this.fetchFolders();

      // Auto-focus input when loading finishes
      this.$watch('loading', value => {
        if (!value) {
          this.$nextTick(() => {
            const input = document.querySelector('.chat-input-form input');
            if (input && !input.disabled) input.focus();
          });
        }
      });
    },

    // ── Helpers ───────────────────────────────────────────────────────

    getFolderDocuments(folderId) {
      return this.documentsByFolder[folderId] || [];
    },

    getFolderConversations(folderId) {
      return this.conversationsByFolder[folderId] || [];
    },

    // ── WebSocket ─────────────────────────────────────────────────────

    connectWs() {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      this.ws = new WebSocket(`${proto}://${location.host}/ws/chat`);
      this.ws.onmessage = (e) => this.handleWsMessage(JSON.parse(e.data));
      this.ws.onclose = () => {
        if (this.loading) {
          this.loading = false;
          this.currentStreamText = '';
          this.currentSources = [];
          const last = this.messages[this.messages.length - 1];
          if (last && last.role === 'assistant' && !last.done) {
            last.content = '⚠️ Connection lost. Please try again.';
            last.done = true;
          } else if (!last || last.role === 'user') {
            this.messages.push({ role: 'assistant', content: '⚠️ Connection lost. Please try again.', done: true, sources: [] });
          }
        }
        setTimeout(() => this.connectWs(), 3000);
      };
      this.ws.onerror = () => {
        if (this.loading) {
          this.loading = false;
          this.currentStreamText = '';
          this.currentSources = [];
          const last = this.messages[this.messages.length - 1];
          if (last && last.role === 'assistant' && !last.done) {
            last.content = '⚠️ Connection error. Please try again.';
            last.done = true;
          } else if (!last || last.role === 'user') {
            this.messages.push({ role: 'assistant', content: '⚠️ Connection error. Please try again.', done: true, sources: [] });
          }
        }
      };
    },

    handleWsMessage(msg) {
      if (msg.type === 'source') {
        this.currentSources.push(msg.data.filename);
      } else if (msg.type === 'conv_id') {
        // Server-assigned conversation ID (created on first query)
        this.activeConvId = msg.data.conv_id;
        // Ensure folder is expanded so the new conversation is visible
        if (this.activeFolderId) {
          this.expandedFolderId = this.activeFolderId;
        }
        this.fetchConversationsForFolder(this.activeFolderId);
      } else if (msg.type === 'disclaimer') {
        // Medical disclaimer from server (hereditary queries)
        this.hereditaryDisclaimer = msg.data.message || '';
      } else if (msg.type === 'token') {
        this.currentStreamText += msg.data.content;
        const last = this.messages[this.messages.length - 1];
        if (last && last.role === 'assistant') {
          last.content = this.currentStreamText;
          last.sources = [...this.currentSources];
        }
        this.scrollChat();
      } else if (msg.type === 'done') {
        const last = this.messages[this.messages.length - 1];
        if (last && last.role === 'assistant') {
          last.done = true;
          last.sources = [...this.currentSources];
        }
        this.loading = false;
        this.currentStreamText = '';
        this.currentSources = [];
        this.fetchDocumentsForFolder(this.activeFolderId);
        this.fetchConversationsForFolder(this.activeFolderId);
      } else if (msg.type === 'error') {
        const last = this.messages[this.messages.length - 1];
        if (last && last.role === 'assistant' && !last.done) {
          last.content = `⚠️ ${msg.data.message}`;
          last.done = true;
        } else {
          this.messages.push({ role: 'assistant', content: `⚠️ ${msg.data.message}`, done: true, sources: [] });
        }
        this.loading = false;
        this.currentStreamText = '';
        this.currentSources = [];
      }
    },

    // ── Folder Dropdown ──────────────────────────────────────────────

    async toggleFolderDropdown(folderId) {
      if (this.expandedFolderId === folderId) {
        // Collapse
        this.expandedFolderId = null;
        return;
      }

      // Expand this folder
      this.expandedFolderId = folderId;
      this.activeFolderId = folderId;
      this.searchAllFolders = false;

      // Load data for this folder
      this.fetchDocumentsForFolder(folderId);
      this.fetchConversationsForFolder(folderId);
    },

    // ── Query ─────────────────────────────────────────────────────────

    sendQuery() {
      const q = this.input.trim();
      if (!q || this.loading) return;

      // If no active conversation, reset conv state but PRESERVE messages
      if (this.activeFolderId && !this.activeConvId) {
        this.activeConvId = null;
        this.searchAllFolders = false;
      }

      this.messages.push({ role: 'user', content: q });
      this.messages.push({ role: 'assistant', content: '', sources: [], done: false });
      this.loading = true;
      this.input = '';
      this.currentStreamText = '';
      this.currentSources = [];

      const payload = {
        type: 'query',
        data: {
          question: q,
          top_k: 5,
          folder_id: this.activeFolderId || null,
          cross_folders: this.searchAllFolders,
          conv_id: this.activeConvId || null,
        }
      };

      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify(payload));
      } else {
        // Fallback to REST
        fetch('/api/query', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            question: q,
            top_k: 5,
            folder_id: this.activeFolderId || null,
            cross_folders: this.searchAllFolders,
          }),
        })
        .then(r => r.json())
        .then(data => {
          const last = this.messages[this.messages.length - 1];
          if (last && last.role === 'assistant') {
            last.content = data.answer;
            last.sources = data.sources;
            last.done = true;
          }
          this.loading = false;
          this.fetchConversationsForFolder(this.activeFolderId);
        })
        .catch(() => {
          const last = this.messages[this.messages.length - 1];
          if (last && last.role === 'assistant') {
            last.content = '⚠️ Failed to get response. Is LM Studio running?';
            last.done = true;
          }
          this.loading = false;
        });
      }
      this.scrollChat();
    },

    // ── Folders ────────────────────────────────────────────────────────

    async fetchFolders() {
      try {
        const r = await fetch('/api/folders');
        const data = await r.json();
        this.folders = data.folders || [];
      } catch {}
    },

    async createFolder() {
      const name = this.newFolderName.trim();
      if (!name) return;

      try {
        const r = await fetch('/api/folders', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: name,
            relationship: this.newFolderRelation,
            notes: '',
          }),
        });
        const data = await r.json();
        this.folders.push(data);
        // Expand and select the new folder
        this.expandedFolderId = data.folder_id;
        this.activeFolderId = data.folder_id;
        this.documentsByFolder[data.folder_id] = [];
        this.conversationsByFolder[data.folder_id] = [];
      } catch (e) {
        alert('Failed to create folder: ' + e.message);
      }
      this.showAddFolder = false;
      this.newFolderName = '';
      this.newFolderRelation = 'self';
    },

    async deleteFolder(folderId) {
      const folder = this.folders.find(f => f.folder_id === folderId);
      if (!folder) return;
      if (!confirm(`Delete ${folder.name} and all their documents and conversations?`)) return;

      try {
        await fetch(`/api/folders/${folderId}`, { method: 'DELETE' });
      } catch {}

      this.folders = this.folders.filter(f => f.folder_id !== folderId);
      delete this.documentsByFolder[folderId];
      delete this.conversationsByFolder[folderId];

      if (this.activeFolderId === folderId) {
        this.activeFolderId = null;
        this.expandedFolderId = null;
        this.activeConvId = null;
        this.messages = [];
      }
    },

    // ── Conversations ──────────────────────────────────────────────────

    async fetchConversationsForFolder(folderId) {
      if (!folderId) return;
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

      // Reset chat state
      this.activeFolderId = folderId;
      this.activeConvId = null;
      this.messages = [];
      this.searchAllFolders = false;
      this.loading = false;
      this.currentStreamText = '';
      this.currentSources = [];
      this.input = '';
      this.expandedFolderId = folderId;
      this.sidebarOpen = false;

      // Create conversation on server immediately (like ChatGPT/Claude)
      try {
        const r = await fetch(`/api/folders/${folderId}/conversations`, { method: 'POST' });
        const data = await r.json();
        if (r.ok) {
          this.activeConvId = data.conv_id;
          // Inject into local list so it appears right away
          const list = this.conversationsByFolder[folderId] || [];
          list.unshift({
            conv_id: data.conv_id,
            folder_id: data.folder_id,
            title: data.title,
            message_count: 0,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
          this.conversationsByFolder[folderId] = list;
          this.showToast('New conversation started');
        } else {
          this.showToast('Failed to start conversation');
        }
      } catch {
        this.showToast('Failed to start conversation');
      }

      this.$nextTick(() => {
        const el = document.querySelector('.chat-input-form input');
        if (el) el.focus();
      });
    },

    async selectConversation(folderId, convId) {
      this.activeFolderId = folderId;
      this.activeConvId = convId;
      this.expandedFolderId = folderId;
      this.searchAllFolders = false;
      try {
        const r = await fetch(`/api/conversations/${folderId}/${convId}`);
        const data = await r.json();
        this.messages = (data.messages || []).map(m => ({
          role: m.role,
          content: m.content,
          sources: m.sources || [],
          done: m.role === 'assistant',
        }));
      } catch {
        this.messages = [];
      }
      this.scrollChat();
      // Close mobile sidebar after selection
      this.sidebarOpen = false;
    },

    async deleteConversation(folderId, convId) {
      try {
        await fetch(`/api/conversations/${folderId}/${convId}`, { method: 'DELETE' });
      } catch {}
      this.conversationsByFolder[folderId] = (this.conversationsByFolder[folderId] || [])
        .filter(c => c.conv_id !== convId);
      if (this.activeConvId === convId) {
        this.activeConvId = null;
        this.messages = [];
      }
    },

    // ── Hereditary Toggle ──────────────────────────────────────────────

    onToggleSearch() {
      // When searching all folders, we still keep the activeFolderId for context
      // but the backend will search across all folders
      if (!this.searchAllFolders) {
        this.hereditaryDisclaimer = '';
      }
    },

    // ── Documents ──────────────────────────────────────────────────────

    async fetchDocumentsForFolder(folderId) {
      if (!folderId) return;
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
      const form = new FormData();
      form.append('file', file);
      if (folderId) {
        form.append('folder_id', folderId);
      }

      try {
        const r = await fetch('/api/documents/upload', { method: 'POST', body: form });
        const data = await r.json();
        if (!r.ok) throw new Error(data.detail || 'Upload failed');
        this.fetchDocumentsForFolder(folderId);
        this.fetchFolders(); // update doc counts
      } catch (e) {
        alert(`Upload failed: ${e.message}`);
      }
      this.uploading = false;
      this.uploadName = '';
    },

    async deleteDoc(docId, folderId) {
      await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
      this.fetchDocumentsForFolder(folderId);
      this.fetchFolders(); // update doc counts
    },

    // ── Per-folder upload trigger ──────────────────────────────────────

    triggerUploadForFolder(folderId) {
      this.pendingUploadFolderId = folderId;
      this.$refs.folderFileInput.click();
    },

    handleFolderFileSelect(e) {
      const files = e.target.files;
      const folderId = this.pendingUploadFolderId || this.activeFolderId;
      for (const f of files) this.uploadFile(f, folderId);
      e.target.value = '';
      this.pendingUploadFolderId = null;
    },

    handleDropForFolder(e, folderId) {
      const files = e.dataTransfer.files;
      for (const f of files) this.uploadFile(f, folderId);
    },

    // ── Status ─────────────────────────────────────────────────────────

    async fetchStatus() {
      try {
        const r = await fetch('/api/status');
        const data = await r.json();
        this.lmstudioConnected = data.lmstudio_connected;
        this.embeddingModel = data.embedding_model;
        this.llmModel = data.llm_model;
      } catch {}
    },

    // ── Utilities ──────────────────────────────────────────────────────

    formatMd(text) {
      if (!text) return '';
      return text
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/### (.+)/g, '<h3>$1</h3>')
        .replace(/## (.+)/g, '<h2>$1</h2>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`(.+?)`/g, '<code>$1</code>')
        .replace(/\n- /g, '\n<li>').replace(/<li>(.+)/g, '<li>$1</li>')
        .replace(/(\n\d+\. )/g, '<br>$1')
        .replace(/\n/g, '<br>');
    },

    scrollChat() {
      requestAnimationFrame(() => {
        const el = document.querySelector('.chat-messages');
        if (el) el.scrollTop = el.scrollHeight;
      });
    },

    // ── Toast ──────────────────────────────────────────────────────────

    toastMessage: '',
    toastVisible: false,
    toastTimer: null,

    showToast(message) {
      this.toastMessage = message;
      this.toastVisible = true;
      if (this.toastTimer) clearTimeout(this.toastTimer);
      this.toastTimer = setTimeout(() => {
        this.toastVisible = false;
      }, 2000);
    },
  }));
});
