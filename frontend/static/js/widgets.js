// ============================================================
// widgets.js — AI Interview Copilot | Overlays & Topic Config
// ============================================================

const { useState, useEffect, useRef } = React;

// ─── Global Constants & Helpers (4 Cohesive Studio Pigments) ───
const TOPICS = [
  { id: "html",               label: "HTML",         icon: "Code2",         color: "#c2410c", category: "Frontend",   group: "Engineering" },
  { id: "css",                label: "CSS",          icon: "Palette",       color: "#c2410c", category: "Frontend",   group: "Engineering" },
  { id: "javascript",         label: "JavaScript",   icon: "Zap",           color: "#c2410c", category: "Frontend",   group: "Engineering" },
  { id: "react",              label: "React",        icon: "Atom",          color: "#c2410c", category: "Frontend",   group: "Engineering" },
  { id: "typescript",         label: "TypeScript",   icon: "FileCode2",     color: "#c2410c", category: "Frontend",   group: "Engineering" },
  { id: "sql",                label: "SQL",          icon: "Database",      color: "#0f766e", category: "Backend",    group: "Engineering" },
  { id: "python",             label: "Python",       icon: "Terminal",      color: "#0f766e", category: "Backend",    group: "Engineering" },
  { id: "nodejs",             label: "Node.js",      icon: "Server",        color: "#0f766e", category: "Backend",    group: "Engineering" },
  { id: "git",                label: "Git",          icon: "GitBranch",     color: "#b45309", category: "Tooling",    group: "Engineering" },
  { id: "dsa",                label: "DSA",          icon: "Cpu",           color: "#b45309", category: "Core CS",    group: "Engineering" },
  { id: "ai_engineer",        label: "AI Engineer",  icon: "Bot",           color: "#0f766e", category: "LLMs & Agents", group: "AI Roles" },
  { id: "ml_engineer",        label: "ML Engineer",  icon: "BrainCircuit",  color: "#c2410c", category: "Deep Learning", group: "AI Roles" },
  { id: "prompt_engineer",    label: "Prompt & RAG", icon: "Sparkles",      color: "#b45309", category: "GenAI & RAG",   group: "AI Roles" },
  { id: "mlops_engineer",     label: "MLOps Infra",  icon: "ServerCog",     color: "#0f766e", category: "AI Systems",    group: "AI Roles" },
  { id: "data_scientist",     label: "Data Science", icon: "BarChart3",     color: "#15803d", category: "Applied ML",    group: "AI Roles" },
  { id: "hotel_management",   label: "Hotel Mgmt",   icon: "Building2",     color: "#15803d", category: "Operations", group: "Business & Ops" },
  { id: "marketing",          label: "Marketing",    icon: "Megaphone",     color: "#15803d", category: "Business",   group: "Business & Ops" },
  { id: "hr",                 label: "HR",           icon: "Users",         color: "#15803d", category: "People",     group: "Business & Ops" },
  { id: "project_management", label: "Project Mgmt", icon: "Kanban",        color: "#15803d", category: "Leadership", group: "Business & Ops" },
  { id: "customer_service",   label: "Cust Service", icon: "Headphones",    color: "#15803d", category: "Support",    group: "Business & Ops" }
];

const DIFFICULTY_COLORS = {
  easy:         { bg: "#ecfdf5", text: "#15803d", border: "#bbf7d0" },
  Beginner:     { bg: "#ecfdf5", text: "#15803d", border: "#bbf7d0" },
  medium:       { bg: "#fffbeb", text: "#b45309", border: "#fde68a" },
  Intermediate: { bg: "#fffbeb", text: "#b45309", border: "#fde68a" },
  hard:         { bg: "#fef2f2", text: "#b91c1c", border: "#fecaca" },
  Advanced:     { bg: "#fef2f2", text: "#b91c1c", border: "#fecaca" },
};

const TIMER_SECONDS = 240;
const shuffle = (arr) => [...arr].sort(() => Math.random() - 0.5);
Object.assign(window, { TOPICS, DIFFICULTY_COLORS, TIMER_SECONDS, shuffle });

// ─── Score Screen Component ───
function ScoreScreen({ score, total, hintsUsed, topic, onRetry, onHome }) {
  const pct = total > 0 ? Math.round((score / total) * 100) : 0;
  const grade = pct >= 80
    ? { title: "Strong Performance", icon: "Award", tone: "sage" }
    : pct >= 60
    ? { title: "Solid Foundation", icon: "CheckCircle2", tone: "ochre" }
    : { title: "Keep Practicing", icon: "BookOpen", tone: "accent" };

  const topicMeta = topic === "resume_tailored"
    ? { id: "resume_tailored", label: "Resume Tailored", icon: "FileText", color: "#c2410c" }
    : topic === "bookmarked"
    ? { id: "bookmarked", label: "Bookmarked", icon: "Bookmark", color: "#b45309" }
    : topic === "missed"
    ? { id: "missed", label: "Retry Missed", icon: "RotateCcw", color: "#0f766e" }
    : TOPICS.find(t => t.id === topic) || { label: "Practice", icon: "Target", color: "#181614" };

  useEffect(() => {
    fetch("/api/save_session", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
      body: JSON.stringify({ topic_id: topic, score, total })
    }).catch(err => console.error(err));
  }, [score, total, topic]);

  return (
    <motion.div
      className="score-screen"
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: EASE_OUT }}
    >
      <div className={`score-badge-icon tone-${grade.tone}`}>
        <LucideIcon name={grade.icon} size={30} strokeWidth={1.75} />
      </div>
      <h2 className="score-title">{grade.title}</h2>
      <p className="score-subtitle">
        <LucideIcon name={topicMeta.icon} size={15} />
        <span>{topicMeta.label} · Session Summary</span>
      </p>

      <div className="score-stats">
        <div className="stat-box">
          <span className="stat-value">{score}/{total}</span>
          <span className="stat-label">Correct</span>
        </div>
        <div className="stat-box stat-box--highlight">
          <span className="stat-value">{pct}%</span>
          <span className="stat-label">Accuracy</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{hintsUsed}</span>
          <span className="stat-label">Hints Used</span>
        </div>
      </div>

      <div className="score-actions">
        <motion.button whileHover={{ y: -1.5 }} whileTap={{ scale: 0.98 }} className="btn btn--secondary" onClick={() => window.print()}>
          <LucideIcon name="Download" size={16} /> Export PDF
        </motion.button>
        <motion.button whileHover={{ y: -1.5 }} whileTap={{ scale: 0.98 }} className="btn btn--accent" onClick={onRetry}>
          <LucideIcon name="RotateCcw" size={16} /> Practice Again
        </motion.button>
        <motion.button whileHover={{ y: -1.5 }} whileTap={{ scale: 0.98 }} className="btn btn--ghost" onClick={onHome}>
          <LucideIcon name="Home" size={16} /> Topics
        </motion.button>
      </div>
    </motion.div>
  );
}
window.ScoreScreen = ScoreScreen;

// ─── ChatBot Component ───
function ChatBot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    { text: "Ask me anything about an interview question, concept, or how to structure your answer.", sender: "bot" }
  ]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) endRef.current.scrollIntoView({ behavior: "smooth" });
  }, [messages, isOpen]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || sending) return;
    setMessages(prev => [...prev, { text, sender: "user" }]);
    setInput("");
    setSending(true);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        text: data.reply || "Sorry, I couldn't respond right now.",
        sender: "bot"
      }]);
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { text: "Network error — please try again.", sender: "bot" }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="chatbot-widget">
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            key="chat-fab"
            className="chatbot-toggle"
            onClick={() => setIsOpen(true)}
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.85, opacity: 0 }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Open AI Interview Copilot chat"
          >
            <LucideIcon name="MessageSquare" size={20} />
            <span>Coach</span>
          </motion.button>
        )}

        {isOpen && (
          <motion.div
            key="chat-win"
            className="chatbot-window"
            initial={{ opacity: 0, y: 16, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 14, scale: 0.97 }}
            transition={{ duration: 0.25, ease: EASE_OUT }}
          >
            <div className="chatbot-header">
              <strong className="chatbot-title">
                <LucideIcon name="Sparkles" size={16} />
                <span>Interview Coach</span>
              </strong>
              <button className="chatbot-close" onClick={() => setIsOpen(false)} aria-label="Close chat">
                <LucideIcon name="X" size={18} />
              </button>
            </div>
            <div className="chatbot-messages">
              {messages.map((m, i) => (
                <div key={i} className={`chatbot-msg ${m.sender === "user" ? "chatbot-msg-user" : "chatbot-msg-bot"}`}>
                  {m.text}
                </div>
              ))}
              {sending && <div className="chatbot-msg chatbot-msg-bot">Thinking…</div>}
              <div ref={endRef} />
            </div>
            <div className="chatbot-input-area">
              <input
                className="chatbot-input"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                placeholder="Ask a question..."
                disabled={sending}
              />
              <button className="chatbot-send" onClick={handleSend} disabled={sending} aria-label="Send message">
                <LucideIcon name="Send" size={15} />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
window.ChatBot = ChatBot;

// ─── Config Modal Component ───
function ConfigModal({ topic, onClose, onStart }) {
  const [difficulty, setDifficulty] = useState("All");
  const [qType, setQType] = useState("All");

  const difficulties = [
    { value: "All",          label: "All Levels",   tone: "ink" },
    { value: "Beginner",     label: "Beginner",     tone: "sage" },
    { value: "Intermediate", label: "Intermediate", tone: "ochre" },
    { value: "Advanced",     label: "Advanced",     tone: "crimson" },
  ];

  const questionTypes = [
    { value: "All", label: "All Types (Mixed)" },
    { value: "theoretical", label: "Theoretical Only" },
    { value: "coding", label: "Coding Only" },
  ];

  const hasTypes = ["html", "css", "javascript", "sql", "react", "python", "typescript", "git", "nodejs", "dsa", "resume_tailored"].includes(topic.id);

  return (
    <motion.div
      className="modal-overlay"
      onClick={onClose}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
    >
      <motion.div
        className="modal-box"
        onClick={e => e.stopPropagation()}
        initial={{ opacity: 0, y: 16, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 10, scale: 0.97 }}
        transition={{ duration: 0.28, ease: EASE_OUT }}
      >
        <div className="modal-head">
          <div className="modal-topic-pill" style={{ color: topic.color }}>
            <LucideIcon name={topic.icon || "Target"} size={16} />
            <span>{topic.label}</span>
          </div>
          <button className="modal-close-x" onClick={onClose} aria-label="Close">
            <LucideIcon name="X" size={18} />
          </button>
        </div>

        <h3 className="modal-title">Configure Session</h3>
        <p className="modal-subtitle">Choose your difficulty and question format before the timer starts.</p>

        <div className="modal-field">
          <label className="modal-label">Difficulty Level</label>
          <div className="modal-options-grid">
            {difficulties.map(d => (
              <motion.button
                key={d.value}
                type="button"
                whileTap={{ scale: 0.97 }}
                className={`modal-option-btn ${difficulty === d.value ? `active tone-${d.tone}` : ""}`}
                onClick={() => setDifficulty(d.value)}
              >
                {d.label}
              </motion.button>
            ))}
          </div>
        </div>

        {hasTypes && (
          <div className="modal-field">
            <label className="modal-label">Question Type</label>
            <div className="modal-options-grid">
              {questionTypes.map(t => (
                <motion.button
                  key={t.value}
                  type="button"
                  whileTap={{ scale: 0.97 }}
                  className={`modal-option-btn ${qType === t.value ? "active" : ""}`}
                  style={t.value === "All" ? { gridColumn: "1 / -1" } : undefined}
                  onClick={() => setQType(t.value)}
                >
                  {t.label}
                </motion.button>
              ))}
            </div>
          </div>
        )}

        <div className="modal-btn-group">
          <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
          <motion.button
            whileHover={{ y: -1.5 }}
            whileTap={{ scale: 0.98 }}
            className="btn btn--accent"
            onClick={() => onStart(topic.id, difficulty, qType)}
          >
            <LucideIcon name="Play" size={15} /> Start Session
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}
window.ConfigModal = ConfigModal;
