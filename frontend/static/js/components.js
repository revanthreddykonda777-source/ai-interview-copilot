// ============================================================
// components.js — AI Interview Copilot | Core UI Elements
// ============================================================

const { useState, useEffect, useRef } = React;

// ─── Timer Component ───
function Timer({ seconds, onExpire }) {
  const [remaining, setRemaining] = useState(seconds);
  const intervalRef = useRef(null);
  const expiredRef = useRef(false);

  useEffect(() => {
    setRemaining(seconds);
    expiredRef.current = false;
  }, [seconds]);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setRemaining(r => (r <= 1 ? 0 : r - 1));
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [seconds]);

  useEffect(() => {
    if (remaining <= 0 && !expiredRef.current) {
      expiredRef.current = true;
      clearInterval(intervalRef.current);
      onExpire();
    }
  }, [remaining, onExpire]);

  const pct = (remaining / seconds) * 100;
  const urgent = remaining <= 20;
  const mins = String(Math.floor(remaining / 60)).padStart(2, "0");
  const secs = String(remaining % 60).padStart(2, "0");

  return (
    <div className={`timer-wrap ${urgent ? "urgent" : ""}`}>
      <div className="timer-track-bar">
        <div
          className="timer-fill-bar"
          style={{
            width: `${pct}%`,
            background: urgent ? "#b91c1c" : "#c2410c"
          }}
        />
      </div>
      <div className="timer-text-label" style={{ color: urgent ? "#b91c1c" : "#6e675f" }}>
        <LucideIcon name="Clock" size={12} />
        <span>{mins}:{secs}</span>
      </div>
    </div>
  );
}
window.Timer = Timer;

// ─── Progress Bar Component ───
function ProgressBar({ current, total }) {
  const pct = total > 0 ? Math.round((current / total) * 100) : 0;
  return (
    <div className="progress-wrap">
      <div className="progress-track">
        <motion.div
          className="progress-fill"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: EASE_OUT }}
        />
      </div>
      <span className="progress-label">{current}/{total}</span>
    </div>
  );
}
window.ProgressBar = ProgressBar;

// ─── Topic Card Component (Interactive 3D Perspective Tilt) ───
function TopicCard({ topic, index = 0, onSelect }) {
  const [tilt, setTilt] = useState({ rx: 0, ry: 0 });
  const reducedMotion = typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const handleMouseMove = (e) => {
    if (reducedMotion) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const px = (e.clientX - rect.left) / rect.width - 0.5;
    const py = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ rx: (-py * 8).toFixed(2), ry: (px * 8).toFixed(2) });
  };

  const resetTilt = () => setTilt({ rx: 0, ry: 0 });

  return (
    <motion.button
      className="topic-card"
      onClick={() => onSelect(topic.id)}
      onMouseMove={handleMouseMove}
      onMouseLeave={resetTilt}
      style={{
        "--accent": topic.color,
        transform: `perspective(850px) rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg)`
      }}
      aria-label={`Practice ${topic.label} questions`}
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index * 0.025, 0.35), ease: EASE_OUT }}
      whileTap={{ scale: 0.985 }}
    >
      <div className="topic-card-top">
        <span className="topic-icon" style={{ color: topic.color }}>
          <LucideIcon name={topic.icon} size={20} strokeWidth={1.8} />
        </span>
        <span className="topic-cat">{topic.category}</span>
      </div>
      <div className="topic-card-bottom">
        <span className="topic-label">{topic.label}</span>
        <span className="topic-count">50 Qs</span>
      </div>
    </motion.button>
  );
}
window.TopicCard = TopicCard;

// ─── Question Card Component ───
function QuestionCard({ question, questionNumber, total, topicId, isBookmarked = false, onToggleBookmark, onCorrect, onSkip, onHint }) {
  const [showAnswer, setShowAnswer] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const [userAnswer, setUserAnswer] = useState("");
  const [timerKey, setTimerKey] = useState(0);
  const [hintClicked, setHintClicked] = useState(false);
  const [gotIt, setGotIt] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [followUp, setFollowUp] = useState(null);
  const [followUpAnswer, setFollowUpAnswer] = useState("");
  const [followUpFeedback, setFollowUpFeedback] = useState(null);
  const [followUpEvalLoading, setFollowUpEvalLoading] = useState(false);
  const [aiFeedback, setAiFeedback] = useState("");
  const [aiScore, setAiScore] = useState(null);
  const [aiCorrect, setAiCorrect] = useState(null);
  const [loading, setLoading] = useState(false);
  const [followUpLoading, setFollowUpLoading] = useState(false);

  const dc = DIFFICULTY_COLORS[question.difficulty] || DIFFICULTY_COLORS.Beginner;
  const recognitionRef = useRef(null);
  const isCodingQuestion = question.type === "coding";
  const wordCount = userAnswer.trim() ? userAnswer.trim().split(/\s+/).length : 0;
  const estSeconds = Math.round((wordCount / 130) * 60);

  const recordAttempt = (passed, scoreVal = 0) => {
    if (!question.id || !topicId) return;
    fetch("/api/record_attempt", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
      body: JSON.stringify({
        question_id: question.id,
        topic_id: topicId,
        passed: Boolean(passed),
        score: scoreVal
      })
    }).catch(() => {});
  };

  useEffect(() => {
    setShowAnswer(false);
    setShowHint(false);
    setUserAnswer("");
    setHintClicked(false);
    setGotIt(false);
    setFollowUp(null);
    setFollowUpAnswer("");
    setFollowUpFeedback(null);
    setTimerKey(k => k + 1);
    setAiFeedback("");
    setAiScore(null);
    setAiCorrect(null);
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, [question.id]);

  useEffect(() => {
    return () => {
      if (window.speechSynthesis) window.speechSynthesis.cancel();
    };
  }, []);

  const toggleSpeakQuestion = () => {
    if (!window.speechSynthesis) return alert("Read aloud is not supported in this browser.");
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(question.question);
    utter.rate = 1;
    utter.onend = () => setIsSpeaking(false);
    utter.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utter);
  };

  useEffect(() => {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      const rec = new SpeechRec();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";
      rec.onresult = (e) => {
        let text = "";
        for (let i = e.resultIndex; i < e.results.length; ++i)
          if (e.results[i].isFinal) text += e.results[i][0].transcript + " ";
        if (text) setUserAnswer(prev => prev + text);
      };
      rec.onerror = () => setIsListening(false);
      rec.onend = () => setIsListening(false);
      recognitionRef.current = rec;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) return alert("Speech recognition is not supported in this browser.");
    isListening ? recognitionRef.current.stop() : (recognitionRef.current.start(), setIsListening(true));
  };

  const handleCheckAnswer = () => {
    if (!userAnswer.trim()) return alert("Please provide an answer first.");
    if (userAnswer.length < 20) alert("That answer seems too short. Try adding a bit more detail.");
    else setShowAnswer(true);
  };

  const handleAskFollowUp = async () => {
    if (!userAnswer.trim()) return alert("Please provide an answer first.");
    setFollowUpLoading(true);
    setFollowUpFeedback(null);
    setFollowUpAnswer("");
    try {
      const res = await fetch("/api/follow_up", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
        body: JSON.stringify({ question: question.question, user_answer: userAnswer })
      });
      const data = await res.json();
      if (data.success && data.follow_up) setFollowUp(data.follow_up);
      else alert(data.error || "Could not generate follow-up.");
    } catch (err) {
      console.error(err);
      alert("Failed to generate follow-up question.");
    } finally {
      setFollowUpLoading(false);
    }
  };

  const handleEvaluateFollowUp = async () => {
    if (!followUpAnswer.trim()) return alert("Please write a reply to the follow-up question.");
    setFollowUpEvalLoading(true);
    try {
      const res = await fetch("/evaluate_answer", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
        body: JSON.stringify({
          question: followUp,
          correct_answer: "",
          user_answer: followUpAnswer
        })
      });
      const data = await res.json();
      if (data.success) {
        setFollowUpFeedback({ score: data.score, feedback: data.feedback, correct: data.correct });
      } else {
        alert(data.error || "Could not evaluate follow-up reply.");
      }
    } catch (err) {
      console.error(err);
      alert("Failed to evaluate follow-up answer.");
    } finally {
      setFollowUpEvalLoading(false);
    }
  };

  const handleTextareaKeyDown = (e) => {
    if (isCodingQuestion && e.key === "Tab") {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const updated = userAnswer.substring(0, start) + "  " + userAnswer.substring(end);
      setUserAnswer(updated);
      requestAnimationFrame(() => {
        e.target.selectionStart = e.target.selectionEnd = start + 2;
      });
    }
  };

  const handleEvaluate = async () => {
    if (!userAnswer.trim()) {
      alert("Please enter your answer first.");
      return;
    }
    setLoading(true);
    setAiFeedback("");
    setAiScore(null);
    setAiCorrect(null);

    try {
      const response = await fetch("/evaluate_answer", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.getCsrfToken ? window.getCsrfToken() : ""
      },
        body: JSON.stringify({
          question: question.question,
          correct_answer: question.answer,
          user_answer: userAnswer
        })
      });
      const data = await response.json();
      if (data.success) {
        setAiFeedback(data.feedback);
        setAiScore(data.score);
        setAiCorrect(data.correct);
        recordAttempt(data.correct, data.score || 0);
      } else {
        alert(data.error || "Evaluation failed");
      }
    } catch (error) {
      console.error(error);
      alert("Failed to evaluate answer.");
    }
    setLoading(false);
  };

  return (
    <motion.div
      key={question.id}
      className="question-card"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: EASE_OUT }}
    >
      <div className="qcard-header">
        <div className="qcard-meta">
          <span className="q-number">Q{questionNumber} / {total}</span>
          <span className="difficulty-badge" style={{ background: dc.bg, color: dc.text, border: `1px solid ${dc.border}` }}>
            {question.difficulty}
          </span>
          <button
            type="button"
            className={`qcard-tool-btn ${isSpeaking ? "is-active" : ""}`}
            onClick={toggleSpeakQuestion}
            title={isSpeaking ? "Stop reading" : "Read question aloud"}
            aria-label={isSpeaking ? "Stop reading question" : "Read question aloud"}
          >
            <LucideIcon name={isSpeaking ? "VolumeX" : "Volume2"} size={14} />
          </button>
          {onToggleBookmark && (
            <button
              type="button"
              className={`qcard-tool-btn ${isBookmarked ? "is-active" : ""}`}
              onClick={() => onToggleBookmark(question.id)}
              title={isBookmarked ? "Remove bookmark" : "Bookmark question"}
              aria-label={isBookmarked ? "Remove bookmark" : "Bookmark question"}
            >
              <LucideIcon name="Bookmark" size={14} />
            </button>
          )}
        </div>
        <Timer key={timerKey} seconds={TIMER_SECONDS} onExpire={() => { recordAttempt(false, 0); onSkip(); }} />
      </div>

      <p className="q-text">{question.question}</p>

      <div className="answer-input-wrap">
        <div className="answer-label-row">
          <label className="answer-input-label">
            {isCodingQuestion ? "Code / Technical Solution (Tab indents)" : "Your Response"}
          </label>
          <div className="qcard-actions-group">
            {wordCount > 0 && (
              <span className="word-stats-pill">
                {wordCount} {wordCount === 1 ? "word" : "words"} · ~{estSeconds}s
              </span>
            )}
            {!showAnswer && (
              <button
                type="button"
                className={`btn btn--mic ${isListening ? "is-recording" : ""}`}
                onClick={toggleListening}
              >
                <LucideIcon name={isListening ? "MicOff" : "Mic"} size={14} />
                <span>{isListening ? "Stop" : "Voice Input"}</span>
              </button>
            )}
          </div>
        </div>
        <textarea
          className={`answer-textarea ${isCodingQuestion ? "answer-textarea--code" : ""}`}
          placeholder={
            isCodingQuestion
              ? "Write your code or algorithm approach here (Tab inserts spaces)..."
              : "Explain your thinking clearly as if speaking to an interviewer..."
          }
          value={userAnswer}
          onChange={e => setUserAnswer(e.target.value)}
          onKeyDown={handleTextareaKeyDown}
          rows={5}
          disabled={showAnswer}
        />
      </div>

      <AnimatePresence>
        {showHint && (
          <motion.div
            key="hint"
            className="hint-box"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <LucideIcon name="Lightbulb" size={17} className="hint-icon" />
            <span>{question.hint}</span>
          </motion.div>
        )}

        {showAnswer && (
          <motion.div
            key="answer"
            className="answer-box"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            <p className="answer-label">
              <LucideIcon name="CheckCircle2" size={15} /> Sample Answer
            </p>
            <p className="answer-text">{question.answer}</p>
          </motion.div>
        )}

        {followUp && (
          <motion.div
            key="followup"
            className="feedback-panel feedback-panel--followup"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <LucideIcon name="MessageSquarePlus" size={17} className="hint-icon" />
            <div className="feedback-body">
              <strong>Follow-up Question</strong>
              <p>{followUp}</p>
              <div className="followup-reply-box">
                <textarea
                  className="answer-textarea followup-reply-textarea"
                  placeholder="Respond to the interviewer's follow-up probe..."
                  value={followUpAnswer}
                  onChange={e => setFollowUpAnswer(e.target.value)}
                  rows={2}
                />
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={handleEvaluateFollowUp}
                  disabled={followUpEvalLoading}
                >
                  <LucideIcon name="Sparkles" size={14} />
                  <span>{followUpEvalLoading ? "Evaluating..." : "Evaluate Follow-up"}</span>
                </button>
              </div>
              {followUpFeedback && (
                <div className="followup-feedback">
                  {followUpFeedback.score !== null && (
                    <span className="feedback-score-tag" style={{ marginBottom: 6, display: "inline-block" }}>
                      Follow-up Score: {followUpFeedback.score}/100
                    </span>
                  )}
                  <div className="feedback-copy">{followUpFeedback.feedback}</div>
                </div>
              )}
            </div>
          </motion.div>
        )}

        {aiFeedback && (
          <motion.div
            key="aifeedback"
            className={`feedback-panel ${aiCorrect ? "feedback-panel--pass" : "feedback-panel--retry"}`}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <LucideIcon name={aiCorrect ? "CheckCircle2" : "AlertCircle"} size={18} className="hint-icon" />
            <div className="feedback-body">
              {aiScore !== null && (
                <div className="feedback-score-line">
                  <strong>{aiCorrect ? "Passed" : "Needs Refinement"}</strong>
                  <span className="feedback-score-tag">{aiScore} / 100</span>
                </div>
              )}
              <div className="feedback-copy">{aiFeedback}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="qcard-actions">
        {!showAnswer && !gotIt && (
          <>
            <div className="qcard-actions-group">
              <motion.button
                whileHover={{ y: -1.5 }}
                whileTap={{ scale: 0.98 }}
                className="btn btn--accent"
                onClick={handleEvaluate}
                disabled={loading}
              >
                <LucideIcon name="ClipboardCheck" size={15} />
                <span>{loading ? "Evaluating..." : "Evaluate Answer"}</span>
              </motion.button>

              <motion.button
                whileHover={{ y: -1.5 }}
                whileTap={{ scale: 0.98 }}
                className="btn btn--secondary"
                onClick={handleAskFollowUp}
                disabled={followUpLoading}
              >
                <LucideIcon name="CornerDownRight" size={15} />
                <span>{followUpLoading ? "Generating..." : "Follow-up"}</span>
              </motion.button>
            </div>

            <div className="qcard-actions-group qcard-actions-right">
              <button className="btn btn--ghost" onClick={handleCheckAnswer}>
                <LucideIcon name="Check" size={15} /> Check
              </button>

              {!showHint && (
                <button
                  className={`btn btn--hint ${hintClicked ? "btn--hint-active" : ""}`}
                  onClick={() => { setShowHint(true); setHintClicked(true); onHint(); }}
                >
                  <LucideIcon name="Lightbulb" size={15} /> Hint
                </button>
              )}

              <button className="btn btn--ghost" onClick={() => setShowAnswer(true)}>
                <LucideIcon name="Eye" size={15} /> Reveal
              </button>
            </div>
          </>
        )}

        {aiFeedback && aiCorrect && !gotIt && (
          <motion.button
            whileHover={{ y: -1.5 }}
            whileTap={{ scale: 0.98 }}
            className="btn btn--correct"
            onClick={() => { setGotIt(true); onCorrect(); }}
          >
            <LucideIcon name="ArrowRight" size={15} /> Next question
          </motion.button>
        )}

        {aiFeedback && !aiCorrect && !gotIt && (
          <button className="btn btn--skip" onClick={() => { recordAttempt(false, aiScore || 0); onSkip(); }}>
            <LucideIcon name="SkipForward" size={15} /> Skip Question
          </button>
        )}

        {showAnswer && !gotIt && (
          <div className="qcard-actions-group">
            <motion.button
              whileHover={{ y: -1.5 }}
              whileTap={{ scale: 0.98 }}
              className="btn btn--correct"
              onClick={() => { recordAttempt(true, 100); setGotIt(true); setTimeout(() => onCorrect(), 350); }}
            >
              <LucideIcon name="Check" size={15} /> Mark Correct
            </motion.button>
            <button className="btn btn--skip" onClick={() => { recordAttempt(false, 0); onSkip(); }}>
              <LucideIcon name="ArrowRight" size={15} /> Next
            </button>
          </div>
        )}
      </div>
    </motion.div>
  );
}
window.QuestionCard = QuestionCard;
