// ============================================================
// app.js — AI Interview Copilot | Application Flow
// ============================================================

const { useState, useEffect, useCallback } = React;

function App() {
  const [screen, setScreen] = useState("home");
  const [topic, setTopic] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [qIndex, setQIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [resumeSkills, setResumeSkills] = useState([]);
  const [loggedIn, setLoggedIn] = useState(false);
  const [bookmarkIds, setBookmarkIds] = useState([]);
  const [missedCount, setMissedCount] = useState(0);
  const [hasAnalysis, setHasAnalysis] = useState(false);
  const [configTopic, setConfigTopic] = useState(null);
  const [activeGroup, setActiveGroup] = useState("All");
  const [theme, setTheme] = useState(() => localStorage.getItem("copilot_theme") || "light");

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("copilot_theme", theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => (t === "light" ? "dark" : "light"));

  const refreshUserMeta = useCallback(() => {
    fetch("/api/user_info")
      .then(res => res.json())
      .then(data => {
        setLoggedIn(Boolean(data.logged_in));
        if (data.resume_skills) setResumeSkills(data.resume_skills);
        setMissedCount(data.missed_count || 0);
        setHasAnalysis(Boolean(data.has_analysis));
        if (data.logged_in) {
          fetch("/api/bookmarks")
            .then(r => r.json())
            .then(b => setBookmarkIds(b.bookmark_ids || []))
            .catch(() => {});
        }
      })
      .catch(err => console.error(err));
  }, []);

  useEffect(() => {
    const hash = window.location.hash;
    if (hash === "#resume_tailored" || hash === "#bookmarked" || hash === "#missed") {
      setTimeout(() => startQuiz(hash.slice(1)), 100);
      window.history.replaceState(null, null, " ");
    }
    refreshUserMeta();
  }, [refreshUserMeta]);

  const toggleBookmark = useCallback(async (questionId) => {
    if (!loggedIn) {
      alert("Please sign in to bookmark questions for later review.");
      return;
    }
    try {
      const res = await fetch("/api/bookmarks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
        },
        body: JSON.stringify({ question_id: questionId })
      });
      const data = await res.json();
      if (data.success && Array.isArray(data.bookmark_ids)) {
        setBookmarkIds(data.bookmark_ids);
      }
    } catch (err) {
      console.error(err);
    }
  }, [loggedIn]);

  const startQuiz = useCallback(async (topicId, diff = "All", type = "All") => {
    setIsLoading(true);
    setConfigTopic(null);
    try {
      const url = `/api/questions/${topicId}?difficulty=${diff}&type=${type}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.length === 0) {
        alert("No questions found matching those filters. Please try another combination.");
        setIsLoading(false);
        return;
      }

      setTopic(topicId);
      setQuestions(topicId === "resume_tailored" ? data : shuffle(data));
      setQIndex(0);
      setScore(0);
      setHintsUsed(0);
      setScreen("quiz");
    } catch (err) {
      console.error(err);
      alert("Failed to load questions. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const advance = useCallback(() => {
    setQIndex(i => {
      if (i + 1 >= questions.length) { setScreen("score"); return i; }
      return i + 1;
    });
  }, [questions.length]);

  const handleCorrect = useCallback(() => {
    setScore(s => s + 1);
    advance();
  }, [advance]);

  const handleSkip = useCallback(() => advance(), [advance]);
  const handleHint = useCallback(() => setHintsUsed(h => h + 1), []);
  const handleRetry = () => startQuiz(topic);
  const handleHome = () => {
    setScreen("home");
    refreshUserMeta();
  };

  const currentTopic = topic === "resume_tailored"
    ? { id: "resume_tailored", label: "Resume Tailored", icon: "FileText", color: "#c2410c" }
    : topic === "bookmarked"
    ? { id: "bookmarked", label: "Bookmarked", icon: "Bookmark", color: "#b45309" }
    : topic === "missed"
    ? { id: "missed", label: "Retry Missed", icon: "RotateCcw", color: "#0f766e" }
    : TOPICS.find(t => t.id === topic) || {};

  const trackSections = [
    { key: "AI Roles",       title: "AI & Data Roles",       icon: "Bot",       isAI: true },
    { key: "Engineering",    title: "Software Engineering",  icon: "Code2",     isAI: false },
    { key: "Business & Ops", title: "Business & Operations", icon: "Briefcase", isAI: false }
  ];

  const visibleSections = activeGroup === "All"
    ? trackSections
    : trackSections.filter(s => s.key === activeGroup);

  return (
    <div className="app-shell">
      <ThreeBackground dimmed={screen === "quiz"} theme={theme} />

      <div className="app">
        <AnimatePresence mode="wait">
          {screen === "home" && (
            <motion.div
              key="screen-home"
              className="home-screen"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35, ease: EASE_OUT }}
            >
              <nav className="top-nav">
                <div className="brand-mark">
                  <span className="brand-dot" />
                  <span>Interview Copilot</span>
                </div>
                <div className="top-nav-links">
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={toggleTheme}
                    aria-label={theme === "light" ? "Switch to dark espresso theme" : "Switch to warm paper theme"}
                    title={theme === "light" ? "Dark Espresso Theme" : "Warm Paper Theme"}
                  >
                    <LucideIcon name={theme === "light" ? "Moon" : "Sun"} size={15} />
                  </button>
                  {loggedIn ? (
                    <>
                      <a href="/resume" className="btn btn--ghost btn--sm">
                        <LucideIcon name="FileUp" size={15} /> Resume
                      </a>
                      <a href="/progress" className="btn btn--ghost btn--sm">
                        <LucideIcon name="TrendingUp" size={15} /> Progress
                      </a>
                      <a href="/dashboard" className="btn btn--primary btn--sm">
                        <LucideIcon name="LayoutDashboard" size={15} /> Dashboard
                      </a>
                    </>
                  ) : (
                    <>
                      <a href="/register" className="btn btn--ghost btn--sm">Create Account</a>
                      <a href="/login" className="btn btn--primary btn--sm">
                        <LucideIcon name="LogIn" size={15} /> Sign In
                      </a>
                    </>
                  )}
                </div>
              </nav>

              <header className="home-header">
                <div className="hero-kicker">
                  <LucideIcon name="Compass" size={14} />
                  <span>Structured Interview Studio</span>
                </div>
                <h1 className="hero-title">
                  Practice like it’s the <span className="hero-title-accent">real conversation.</span>
                </h1>
                <p className="home-tagline">
                  Timed technical and behavioral drills, resume-tailored questions, and direct AI feedback across {TOPICS.length} disciplines.
                </p>
                {isLoading && <p className="loading-inline">Loading question bank…</p>}
                <div className="home-stats">
                  <span className="home-stat"><LucideIcon name="Layers" size={14} /> {TOPICS.length} Tracks</span>
                  <span className="home-stat"><LucideIcon name="BookOpen" size={14} /> {TOPICS.length * 50} Questions</span>
                  <span className="home-stat"><LucideIcon name="Clock" size={14} /> 4 min / question</span>
                </div>
              </header>

              {loggedIn && resumeSkills.length > 0 && (
                <section className="resume-spotlight">
                  <div className="resume-spotlight-copy">
                    <span className="resume-spotlight-kicker">
                      <LucideIcon name="FileText" size={14} /> Resume Ready
                    </span>
                    <h3>Practice your personalized resume questions</h3>
                    <div className="resume-skill-chips">
                      {resumeSkills.slice(0, 6).map((sk, idx) => (
                        <span key={idx} className="resume-skill-chip">{sk}</span>
                      ))}
                      {resumeSkills.length > 6 && (
                        <span className="resume-skill-chip">+{resumeSkills.length - 6} more</span>
                      )}
                    </div>
                  </div>
                  <div className="qcard-actions-group">
                    {hasAnalysis && (
                      <a href="/analysis" className="btn btn--secondary">
                        <LucideIcon name="FileCheck2" size={15} /> View Report
                      </a>
                    )}
                    <motion.button
                      whileHover={{ y: -1.5 }}
                      whileTap={{ scale: 0.98 }}
                      className="btn btn--accent"
                      onClick={() => startQuiz("resume_tailored")}
                    >
                      <LucideIcon name="Play" size={15} /> Start Resume Track
                    </motion.button>
                  </div>
                </section>
              )}

              {loggedIn && (bookmarkIds.length > 0 || missedCount > 0) && (
                <div className="review-decks-bar">
                  <span className="review-decks-label">
                    <LucideIcon name="FolderHeart" size={14} /> Personal Review Decks
                  </span>
                  <div className="qcard-actions-group">
                    {bookmarkIds.length > 0 && (
                      <button type="button" className="btn btn--secondary btn--sm" onClick={() => startQuiz("bookmarked")}>
                        <LucideIcon name="Bookmark" size={14} /> Bookmarked ({bookmarkIds.length})
                      </button>
                    )}
                    {missedCount > 0 && (
                      <button type="button" className="btn btn--secondary btn--sm" onClick={() => startQuiz("missed")}>
                        <LucideIcon name="RotateCcw" size={14} /> Retry Missed ({missedCount})
                      </button>
                    )}
                  </div>
                </div>
              )}

              <section className="topics-section">
                <div className="section-head">
                  <h2 className="section-title">Select a Track</h2>
                  <div className="filter-tabs" role="tablist" aria-label="Filter tracks">
                    {["All", "AI Roles", "Engineering", "Business & Ops"].map(grp => (
                      <button
                        key={grp}
                        type="button"
                        role="tab"
                        aria-selected={activeGroup === grp}
                        className={`filter-tab ${activeGroup === grp ? "active" : ""}`}
                        onClick={() => setActiveGroup(grp)}
                      >
                        {grp}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="track-sections-stack">
                  {visibleSections.map(sec => {
                    const secTopics = TOPICS.filter(t => t.group === sec.key);
                    return (
                      <motion.div
                        key={sec.key}
                        className={`track-group-block ${sec.isAI ? "track-group-block--ai" : ""}`}
                        initial={{ opacity: 0, y: 24 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true, amount: 0.1 }}
                        transition={{ duration: 0.45, ease: EASE_OUT }}
                      >
                        <div className="track-group-header">
                          <h3 className="track-group-title">
                            <LucideIcon name={sec.icon} size={16} />
                            <span>{sec.title}</span>
                          </h3>
                          <span className={`track-group-badge ${sec.isAI ? "track-group-badge--ai" : ""}`}>
                            {secTopics.length} Tracks · {secTopics.length * 50} Qs
                          </span>
                        </div>
                        <div className="topics-grid">
                          {secTopics.map((t, idx) => (
                            <TopicCard key={t.id} topic={t} index={idx} onSelect={() => setConfigTopic(t)} />
                          ))}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </section>

              <footer className="home-footer">
                <div className="home-footer-brand">
                  <span>AI Interview Copilot</span>
                  <span>·</span>
                  <span>Practice · Evaluate · Refine</span>
                </div>
                <div className="home-footer-links">
                  <a href="/faq">FAQ</a>
                  <a href="/privacy">Privacy</a>
                  <a href="/statements">Statements</a>
                </div>
              </footer>
            </motion.div>
          )}

          {screen === "quiz" && questions.length > 0 && (
            <motion.div
              key="screen-quiz"
              className="quiz-screen"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3, ease: EASE_OUT }}
            >
              <div className="quiz-topbar">
                <button id="back-home-btn" className="btn btn--ghost btn--sm" onClick={handleHome}>
                  <LucideIcon name="ArrowLeft" size={15} /> Tracks
                </button>
                <span className="quiz-topic-label">
                  <LucideIcon name={currentTopic.icon || "Target"} size={16} />
                  <span>{currentTopic.label}</span>
                </span>
                <span className="score-live">
                  <LucideIcon name="CheckCircle2" size={14} />
                  <span>{score}</span>
                </span>
              </div>
              <ProgressBar current={qIndex} total={questions.length} />
              <QuestionCard
                question={questions[qIndex]}
                questionNumber={qIndex + 1}
                total={questions.length}
                topicId={topic}
                isBookmarked={bookmarkIds.includes(questions[qIndex].id)}
                onToggleBookmark={toggleBookmark}
                onCorrect={handleCorrect}
                onSkip={handleSkip}
                onHint={handleHint}
              />
            </motion.div>
          )}

          {screen === "score" && (
            <ScoreScreen
              key="screen-score"
              score={score}
              total={questions.length}
              hintsUsed={hintsUsed}
              topic={topic}
              onRetry={handleRetry}
              onHome={handleHome}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {configTopic && (
            <ConfigModal
              key="config-modal"
              topic={configTopic}
              onClose={() => setConfigTopic(null)}
              onStart={startQuiz}
            />
          )}
        </AnimatePresence>

        <ChatBot />
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(<App />);
