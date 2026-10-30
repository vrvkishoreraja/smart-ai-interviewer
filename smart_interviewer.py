#!/usr/bin/env python3
"""
Smart AI Interviewer CLI
========================
An intelligent, role-based interview simulation tool that:
1. Conducts dynamic, structured interview questions based on the candidate's chosen role and level.
2. Accepts candidate answers step-by-step.
3. Automatically triggers a comprehensive feedback report when the candidate types 'end'.
4. Identifies exact strengths, skill gaps, model answers, and personalized improvement areas.

Can run with:
- Standard Python (no dependencies, built-in intelligent NLP heuristic engine)
- Gemini API (if GEMINI_API_KEY environment variable or key is supplied)
"""

import sys
import os
import json
import time
import datetime
import urllib.request
import urllib.error
import re

# Ensure safe UTF-8 terminal encoding on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Terminal color codes for cross-platform styling
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'
    RESET = '\033[0m'

# Pre-curated role question banks for instant, zero-dependency offline mode
ROLE_QUESTION_BANKS = {
    "software engineer": [
        {
            "category": "Core Fundamentals",
            "question": "Can you explain the difference between processes and threads, and how memory and concurrency are managed between them?",
            "keywords": ["memory", "shared", "stack", "heap", "isolation", "overhead", "context switch", "race condition", "lock", "thread", "process"],
            "model_answer": "Processes are independent execution units with their own isolated memory address space (heap, stack, code). Threads exist within a process and share its heap and code segment, but each maintains its own stack and registers. Concurrency with threads is lightweight but requires synchronization primitives (mutexes, semaphores) to avoid race conditions. Processes provide fault isolation but have higher IPC (Inter-Process Communication) and context-switching overhead."
        },
        {
            "category": "Practical Problem Solving & Debugging",
            "question": "Imagine your production backend service suddenly experiences a spike in API latency from 50ms to 3000ms, but CPU usage remains below 20%. How would you isolate and diagnose the root cause?",
            "keywords": ["database", "connection pool", "io", "bottleneck", "external api", "lock", "thread pool", "logs", "distributed tracing", "profiler", "network"],
            "model_answer": "Low CPU with high latency strongly suggests an I/O wait, connection starvation, or thread blocking rather than computational bottlenecks. I would check distributed traces (OpenTelemetry/Jaeger) to identify slow downstream spans; inspect database connection pool saturation, slow queries, or deadlocks; verify third-party HTTP timeouts; and review thread dump metrics to see if threads are waiting on synchronization locks or socket reads."
        },
        {
            "category": "System Design & Optimization",
            "question": "How would you design an idempotent payment processing API to ensure users are never charged twice when network retries occur?",
            "keywords": ["idempotency key", "database", "unique constraint", "distributed lock", "atomic", "redis", "status", "retry", "transaction"],
            "model_answer": "Clients must pass a unique client-generated Idempotency-Key in header. The server acquires a lock or executes an atomic insert into an idempotency records table with a UNIQUE constraint. If the key already exists and is 'PROCESSING', subsequent calls return HTTP 409 or wait. If already 'SUCCEEDED', it returns the cached response directly without re-charging. Database transactions ensure payment status and ledger updates commit together atomically."
        },
        {
            "category": "Behavioral & Technical Trade-offs",
            "question": "Tell me about a time you had to push back on a product feature or deadline due to technical debt, security, or architectural risks. How did you handle the situation?",
            "keywords": ["stakeholder", "trade-off", "risk", "compromise", "communication", "impact", "alternative", "data", "timeline"],
            "model_answer": "A strong answer uses the STAR method (Situation, Task, Action, Result). It highlights translating technical risk into business impact (e.g., risk of data loss, downtime cost, or compliance liability), presenting concrete phased alternatives (e.g., MVP release with planned follow-up sprint), aligning with product stakeholders, and delivering the feature safely without alienating the team."
        }
    ],
    "frontend developer": [
        {
            "category": "Core Fundamentals",
            "question": "Can you explain how the browser Critical Rendering Path works from receiving HTML to painting pixels, and how you optimize it?",
            "keywords": ["dom", "cssom", "render tree", "layout", "reflow", "paint", "composite", "async", "defer", "critical css"],
            "model_answer": "The browser parses HTML to construct the DOM, and CSS to construct the CSSOM. These combine into the Render Tree, followed by Layout (computing geometry and dimensions) and Painting (filling pixels onto layers), and finally Compositing. Optimization includes minimizing render-blocking CSS/JS using defer/async, code splitting, inlining critical CSS, minimizing layout thrashing (avoiding forced synchronous reflows), and leveraging GPU compositing (transform/opacity)."
        },
        {
            "category": "State Management & Performance",
            "question": "In a large single-page application (React/Vue/Angular), what strategies do you use to eliminate unnecessary component re-renders and keep UI interactions at 60fps?",
            "keywords": ["memo", "usecallback", "usememo", "virtualization", "profiler", "immutable", "state colocation", "props", "debounce"],
            "model_answer": "Colocate state as close to leaves as possible rather than storing everything in global state; use memoization (React.memo, useMemo, useCallback) with proper dependency arrays; implement list virtualization (e.g. react-window) for long lists; debounce high-frequency events like search or window resizing; use the React DevTools Profiler to identify culprit renders; and ensure stable object/array references in props."
        },
        {
            "category": "Architecture & Modern Standards",
            "question": "How do you evaluate and implement Core Web Vitals (LCP, INP, CLS) improvements on an e-commerce or content-heavy web app?",
            "keywords": ["lcp", "inp", "cls", "image optimization", "preload", "fonts", "aspect ratio", "web workers", "main thread"],
            "model_answer": "For LCP (Largest Contentful Paint): preload hero images, use modern formats (AVIF/WebP) with responsive srcset, and avoid client-side rendering bottlenecks. For INP (Interaction to Next Paint): break long tasks using scheduler.yield() or requestIdleCallback, offload heavy calculations to Web Workers, and keep event handlers lean. For CLS (Cumulative Layout Shift): reserve dimensions on images/ads using explicit width/height or aspect-ratio CSS, and use font-display: optional or size-adjust."
        },
        {
            "category": "Accessibility & Testing",
            "question": "How do you ensure a complex custom UI widget (like an accessible combobox or modal dialog) conforms to WCAG AA guidelines?",
            "keywords": ["aria", "keyboard", "focus trap", "screen reader", "tabindex", "escape", "contrast", "wcag", "semantic"],
            "model_answer": "Ensure full keyboard navigability (Tab, Shift+Tab, Arrow keys, Enter, Space, Escape to close). For modals, manage a focus trap to prevent tabbing into background elements, set role='dialog', aria-modal='true', and aria-labelledby. Restore focus to the trigger button upon closing. Ensure color contrast ratios meet at least 4.5:1 for normal text, and test using screen readers (NVDA/VoiceOver) and automated accessibility linters (axe-core)."
        }
    ],
    "data scientist": [
        {
            "category": "Statistics & Modeling Fundamentals",
            "question": "How do you identify and handle severe class imbalance in a classification problem where the positive class is less than 1% of the data?",
            "keywords": ["smote", "undersampling", "oversampling", "pr-auc", "f1", "precision", "recall", "cost-sensitive", "class weight", "stratified"],
            "model_answer": "Avoid accuracy as a metric; use PR-AUC (Precision-Recall Area Under Curve), F1-score, or cost-sensitive matrices. Techniques include resampling: stratified K-Fold split, synthetic minority oversampling (SMOTE) on train set only, or random under-sampling. Algorithmic adjustments include class weighting (scale_pos_weight in XGBoost, balanced class weights). Threshold tuning: calibrate predicted probabilities and choose the decision threshold that maximizes business utility."
        },
        {
            "category": "Feature Engineering & Leakage",
            "question": "What is data leakage in machine learning pipelines, what are common sneaky examples of it, and how do you guarantee prevention?",
            "keywords": ["data leakage", "train test split", "preprocessing", "cross validation", "target leakage", "pipeline", "time series"],
            "model_answer": "Data leakage occurs when information from outside the training dataset is inadvertently used to create the model, leading to overly optimistic evaluation that fails in production. Common sneaky examples include fitting scalers/imputers before splitting train/val, using future features in time-series data, or feature engineering across grouped entities where target signals bleed. Prevention: strictly fit transformers inside scikit-learn Pipelines on training splits only, and use time-based rolling splits for temporal data."
        },
        {
            "category": "Model Evaluation & Business Impact",
            "question": "A business stakeholder asks why you chose an ensemble model with 88% precision over a simpler linear model with 84% accuracy. How do you explain this decision quantitatively and qualitatively?",
            "keywords": ["false positive", "business cost", "precision", "recall", "explainability", "shap", "roi", "trade-off", "value"],
            "model_answer": "Frame the difference in terms of cost and business risk. If false positives are expensive (e.g. fraud alerts freezing legitimate accounts or spamming VIP customers), high precision directly protects revenue and user trust. Explain that 84% accuracy could be worse than a naive baseline if classes are imbalanced. Provide feature importance or SHAP explanations to demonstrate that the ensemble captures non-linear interactions without sacrificing decision interpretability."
        },
        {
            "category": "Deployment & MLOps",
            "question": "How do you detect and mitigate data drift and concept drift in a model deployed in production?",
            "keywords": ["data drift", "concept drift", "ks test", "psi", "monitoring", "retraining", "ground truth", "evidently", "baseline"],
            "model_answer": "Data drift (covariate shift) is when input distributions change (P(X) changes); concept drift is when the relationship between features and target changes (P(Y|X) changes). Detection: monitor statistical divergence metrics like Population Stability Index (PSI), Kolmogorov-Smirnov test, or Wasserstein distance between inference batches and training baseline. Mitigation: establish automated alerts, maintain continuous shadow evaluation against incoming ground-truth labels, and trigger scheduled or performance-gated retraining pipelines."
        }
    ],
    "devops engineer": [
        {
            "category": "Infrastructure as Code & CI/CD",
            "question": "How do you structure a production-grade Terraform pipeline across multiple environments (Dev, Staging, Prod) to prevent drift and blast radius?",
            "keywords": ["state file", "remote backend", "s3", "gcs", "lock", "modules", "blast radius", "terragrunt", "workspaces", "drift"],
            "model_answer": "Use isolated state files per environment and per subsystem (e.g. networking, databases, compute) using remote backends with state locking (S3 + DynamoDB or GCS). Avoid a monolithic state file to minimize blast radius. Reuse tested versioned Terraform modules. Enforce CI/CD automation where `terraform plan` is reviewed on PRs and `terraform apply` executes via pipeline with approval gates. Implement scheduled drift detection runs to catch manual console changes."
        },
        {
            "category": "Kubernetes & Container Orchestration",
            "question": "A pod in Kubernetes enters a CrashLoopBackOff state. Walk me through your step-by-step diagnostic workflow to fix it.",
            "keywords": ["kubectl describe", "kubectl logs", "exit code", "oomkilled", "liveness", "readiness", "events", "configmap", "secret"],
            "model_answer": "1. Run `kubectl describe pod <name>` to inspect Events, recent state, termination reason, and exit code. 2. If exit code is 137 (OOMKilled), increase container memory limits. 3. If exit code is 0 or 1, check application logs with `kubectl logs <name> --previous` to see runtime crashes or unhandled exceptions. 4. Verify environment variables, mounted ConfigMaps, and Secrets. 5. Inspect liveness/readiness probes to ensure they aren't failing due to slow application boot times."
        },
        {
            "category": "Zero-Downtime Deployments & Traffic Routing",
            "question": "Explain how you design a Blue-Green vs Canary deployment strategy for high-traffic microservices, and what metrics trigger an automated rollback.",
            "keywords": ["canary", "blue green", "ingress", "istio", "metrics", "error rate", "latency", "rollback", "prometheus", "slo"],
            "model_answer": "Blue-Green deploys an entire identical new environment (Green) and switches router/ingress pointer instantaneously once validated; easy rollback but requires 2x resource headroom. Canary routes a small fraction (e.g., 2% -> 10% -> 50%) of live traffic to the new version using service mesh (Istio) or ingress controllers (Argo Rollouts). Automated rollback is triggered if 5xx error rate spikes above threshold, P99 latency degrades past SLO, or synthetic health checks fail."
        },
        {
            "category": "Incident Management & Reliability",
            "question": "Describe your incident response framework during a major SEV-1 production outage, from initial alert to post-mortem.",
            "keywords": ["incident commander", "communication", "mitigation", "post-mortem", "blameless", "timeline", "action items", "pagerduty"],
            "model_answer": "Designate an Incident Commander (IC) to lead coordination, a Tech Lead to drive diagnostics, and a Communications Lead to update status pages. Priority is mitigation first (rollback, failover, traffic throttling) rather than root-cause fixing in place. Maintain an active incident timeline. Once resolved, conduct a blameless post-mortem within 48 hours to identify contributing factors, update runbooks, and assign preventative action items with explicit owners."
        }
    ],
    "product manager": [
        {
            "category": "Product Strategy & Prioritization",
            "question": "How do you prioritize competing feature requests from enterprise sales, user feedback, and technical engineering debt?",
            "keywords": ["framework", "rice", "ice", "business goals", "impact", "effort", "okr", "trade-off", "sales", "debt"],
            "model_answer": "Anchor decisions on core company OKRs and product vision. Use quantitative prioritization frameworks like RICE (Reach, Impact, Confidence, Effort) to calibrate objectively. Categorize requests into strategic themes: allocate capacity percentages (e.g., 60% customer value & features, 20% technical debt & stability, 20% growth/sales bets). Validate sales asks against broader market demand to avoid building one-off custom features that don't scale."
        },
        {
            "category": "Metrics & Data-Driven Decisions",
            "question": "You launch a new onboarding flow and observe that sign-ups increased by 15%, but Day-30 retention dropped by 8%. How do you analyze and resolve this problem?",
            "keywords": ["funnel", "cohort analysis", "intent", "activation", "quality", "retention", "user interviews", "experiment"],
            "model_answer": "The increased sign-ups likely lowered the barrier to entry, attracting lower-intent users or skipping key activation milestones needed for long-term habit formation. I would perform cohort analysis comparing retained vs churned users to see where drop-offs happen in the product lifecycle; evaluate feature adoption; interview churning users to discover unfulfilled expectations; and test introducing progressive profiling or guided onboarding steps that boost activation."
        },
        {
            "category": "Cross-Functional Leadership & Conflict",
            "question": "Your engineering lead tells you an agreed-upon MVP cannot be delivered on schedule unless scope is cut in half. How do you approach this conversation and align stakeholders?",
            "keywords": ["mvp", "scope", "must have", "negotiation", "timeline", "user value", "trade-off", "stakeholders"],
            "model_answer": "Empathize and collaborate rather than pushing back blindly. Ask the tech lead to break down the architectural bottlenecks. Apply the MoSCoW method to identify the true non-negotiable core hypothesis of the MVP (what is essential to deliver user value). Trim nice-to-haves and defer edge-case automation to phase 2. Communicate proactively to executive stakeholders with the revised scope, trade-off rationale, and phased release plan."
        },
        {
            "category": "Discovery & Execution",
            "question": "Walk me through how you conduct customer discovery to validate a problem before writing a single line of code or PRD.",
            "keywords": ["interviews", "problem validation", "open-ended", "user research", "mom test", "pain points", "willingness to pay"],
            "model_answer": "Focus on the user's current behaviors and actual past pain points rather than asking hypothetical questions (following 'The Mom Test' principles). Ask open-ended questions like 'How do you currently solve X?' and 'What is the most frustrating part of that process?'. Look for evidence of existing makeshift workarounds or budget spend. Synthesize findings into key personas and job-to-be-done statements, and test low-fidelity prototypes or landing page tests before writing specs."
        }
    ]
}

def clean_text(text):
    return text.strip()

def call_gemini_api(api_key, prompt, model="gemini-2.5-flash"):
    """Call Google Gemini REST API using standard urllib.request (zero dependencies)."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            candidates = res_data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode("utf-8")
        return f"[API Error {e.code}]: {error_msg}"
    except Exception as e:
        return f"[Connection Error]: {str(e)}"
    return ""

def generate_dynamic_questions(role, level="Mid-Level", api_key=None):
    """Generate interview questions for any role."""
    normalized_role = role.lower().strip()
    
    # Check if we have exact match in offline question banks
    for bank_role, questions in ROLE_QUESTION_BANKS.items():
        if bank_role in normalized_role or normalized_role in bank_role:
            return questions
            
    # If API key is available, call Gemini to get tailored questions
    if api_key:
        prompt = f"""You are an expert technical interviewer hiring for a {level} {role}.
Generate exactly 4 realistic, progressive interview questions tailored specifically to this role:
1. Core Technical / Theoretical Concept
2. Practical Scenario & Debugging / Edge Cases
3. Architecture, System Design, or Best Practices
4. Behavioral / Situational Trade-offs

Return ONLY a valid JSON array of objects with keys: "category", "question", "keywords" (list of 6-10 keywords/concepts expected in a great answer), "model_answer" (a concise 3-4 sentence exemplary answer). Do not wrap in markdown quotes or extra text."""
        response = call_gemini_api(api_key, prompt)
        try:
            # Extract JSON from response
            cleaned = re.sub(r'^```json\s*', '', response.strip())
            cleaned = re.sub(r'\s*```$', '', cleaned)
            parsed = json.loads(cleaned)
            if isinstance(parsed, list) and len(parsed) >= 3:
                return parsed
        except Exception:
            pass

    # Generic high-quality question fallback for custom roles
    return [
        {
            "category": f"Core {role} Competencies",
            "question": f"As a {role}, what are the foundational principles and tools you rely on daily, and why are they critical to your workflow?",
            "keywords": ["workflow", "best practices", "tools", "standards", "efficiency", "collaboration", "quality"],
            "model_answer": f"In a {role} role, success relies on balancing foundational theoretical principles with robust, battle-tested tools. An expert explains their core technical framework, how they maintain high quality and consistency, and how their toolchain accelerates reliable outcomes."
        },
        {
            "category": "Complex Problem Solving & Edge Cases",
            "question": f"Describe a challenging, ambiguous problem you encountered in your work as a {role}. How did you dissect the root cause and deliver a resilient solution?",
            "keywords": ["root cause", "analysis", "data", "trade-off", "debugging", "impact", "resolution"],
            "model_answer": "The candidate should demonstrate structured diagnostic thinking: establishing hypotheses, isolating variables using data or telemetry, testing systematically, implementing an enduring fix, and documenting lessons learned to prevent recurrence."
        },
        {
            "category": "Process, Architecture & Quality Standards",
            "question": f"How do you design and structure your projects or deliverables for long-term scalability, maintainability, and team collaboration?",
            "keywords": ["scalability", "documentation", "testing", "maintainability", "modular", "reusable", "standards"],
            "model_answer": "Emphasizes modular design, clean separation of concerns, thorough documentation, automated testing or validation gates, and adhering to industry standards so teammates can onboard and contribute seamlessly."
        },
        {
            "category": "Stakeholder Collaboration & Conflict",
            "question": "Can you describe a situation where you had a strong disagreement with a colleague or stakeholder regarding a technical or project direction? How did you resolve it?",
            "keywords": ["communication", "listening", "objective", "compromise", "alignment", "data-driven", "outcome"],
            "model_answer": "Follows the STAR method, focusing on active listening, bringing objective metrics or user needs to the discussion, depersonalizing the conflict, and reaching an aligned decision that prioritized project success."
        }
    ]

def evaluate_interview(role, level, interview_history, api_key=None):
    """
    Evaluates candidate responses and provides detailed feedback,
    scores, strengths, and targeted improvement suggestions.
    """
    if not interview_history:
        return {
            "overall_score": 0,
            "verdict": "Interview Terminated Early",
            "summary": "No questions were answered before ending the interview.",
            "scores": {"technical": 0, "problem_solving": 0, "communication": 0, "practical": 0},
            "strengths": ["Curiosity to explore the interview tool."],
            "improvements": ["Complete at least 2-3 interview questions to receive comprehensive evaluation."],
            "breakdown": []
        }
    
    # If API key is available, use Gemini for human-grade deep evaluation
    if api_key:
        qa_text = ""
        for i, item in enumerate(interview_history, 1):
            qa_text += f"\n--- Question {i} ({item['category']}) ---\n"
            qa_text += f"Question: {item['question']}\n"
            qa_text += f"Candidate Answer: {item['answer']}\n"
            qa_text += f"Expected Points: {', '.join(item.get('keywords', []))}\n"
            
        prompt = f"""You are a top-tier Principal Hiring Manager conducting an interview debrief for a {level} {role}.
Evaluate the candidate's interview performance based on the following transcript:
{qa_text}

Provide an honest, constructive, and actionable assessment.
Return ONLY a valid JSON object with the following schema:
{{
  "overall_score": <number between 1.0 and 10.0 with 1 decimal>,
  "verdict": "<Strong Hire | Hire | Leaning Hire | Needs Work | Not Ready>",
  "summary": "<2-3 sentence executive summary of candidate readiness>",
  "scores": {{
    "technical": <number between 1 and 10>,
    "problem_solving": <number between 1 and 10>,
    "communication": <number between 1 and 10>,
    "practical": <number between 1 and 10>
  }},
  "strengths": [
    "<bullet point 1>",
    "<bullet point 2>",
    "<bullet point 3>"
  ],
  "improvements": [
    "<specific area 1 with concrete advice on what to study or how to answer better>",
    "<specific area 2 with concrete advice>",
    "<specific area 3 with concrete advice>"
  ],
  "breakdown": [
    {{
      "question_num": 1,
      "score": <number between 1 and 10>,
      "feedback": "<specific critique of this answer>",
      "ideal_points": "<key points or terminology that would make this answer top-tier>"
    }}
  ]
}}
Do not wrap in extra markdown or commentary."""
        response = call_gemini_api(api_key, prompt)
        try:
            cleaned = re.sub(r'^```json\s*', '', response.strip())
            cleaned = re.sub(r'\s*```$', '', cleaned)
            parsed = json.loads(cleaned)
            if "overall_score" in parsed and "improvements" in parsed:
                return parsed
        except Exception:
            pass

    # Built-in Intelligent Heuristic Evaluation Engine (Offline / Zero-Config)
    breakdown = []
    total_q_score = 0
    strengths = []
    improvements = []
    
    tech_scores = []
    prob_scores = []
    comm_scores = []
    pract_scores = []
    
    for i, item in enumerate(interview_history, 1):
        ans = item["answer"].strip()
        words = ans.split()
        word_count = len(words)
        keywords = item.get("keywords", [])
        
        # Check keyword presence
        matched_kw = [kw for kw in keywords if kw.lower() in ans.lower()]
        kw_ratio = len(matched_kw) / max(len(keywords), 1)
        
        # Base scoring heuristics
        q_score = 4.0  # Base attempt score
        
        # Depth evaluation
        if word_count < 15:
            q_score = 4.0
            feedback = "Answer was too brief. Interviewers expect structured explanations with concrete details and rationale."
            missing = f"Should elaborate on: {', '.join(keywords[:4])}."
        elif word_count < 40:
            q_score += 1.5
            feedback = "Good initial intuition, but lacks technical depth and real-world examples."
            missing = f"Expand on implementation trade-offs and concepts like {', '.join(keywords[:3])}."
        elif word_count < 100:
            q_score += 3.0
            feedback = "Solid explanation covering the essential concepts clearly."
            missing = f"Could be elevated by mentioning: {', '.join([k for k in keywords if k not in matched_kw][:3])}."
        else:
            q_score += 4.0
            feedback = "Comprehensive and detailed response demonstrating clear domain familiarity."
            missing = "Excellent depth. Focus on keeping the structure crisp using clear headings or steps."
            
        # Keyword bonus
        q_score += min(kw_ratio * 3.0, 2.5)
        
        # Cap score at 10
        q_score = min(round(q_score, 1), 10.0)
        total_q_score += q_score
        
        # Pillar estimates
        comm = min(10, max(4, int(5 + (word_count / 30))))
        tech = min(10, max(4, int(4 + (kw_ratio * 6))))
        prob = min(10, max(4, int(q_score * 0.95)))
        pract = min(10, max(4, int(q_score * 0.9)))
        
        tech_scores.append(tech)
        prob_scores.append(prob)
        comm_scores.append(comm)
        pract_scores.append(pract)
        
        if matched_kw:
            strengths.append(f"Q{i} ({item['category']}): Effectively incorporated core industry concepts like {', '.join(matched_kw[:3])}.")
        if kw_ratio < 0.4 and word_count >= 15:
            improvements.append(f"Q{i} ({item['category']}): Missing key industry terminology. Be sure to reference concepts such as {', '.join(keywords[:3])}.")
        elif word_count < 25:
            improvements.append(f"Q{i} ({item['category']}): Answer was surface-level. Practice the STAR technique (Situation, Task, Action, Result) to provide depth.")
            
        breakdown.append({
            "question_num": i,
            "category": item["category"],
            "question": item["question"],
            "candidate_answer": ans,
            "score": q_score,
            "feedback": feedback,
            "ideal_points": item.get("model_answer", missing)
        })

    avg_score = round(total_q_score / len(interview_history), 1)
    
    # Verdict calculation
    if avg_score >= 8.5:
        verdict = "Strong Hire (Exceptional Performance)"
        summary = f"Demonstrated high domain mastery, strong technical depth, and clear articulation suitable for a {level} {role}."
    elif avg_score >= 7.0:
        verdict = "Hire (Solid Candidate)"
        summary = f"Shows good practical command of core concepts for {role}, with minor opportunities to sharpen architectural trade-offs."
    elif avg_score >= 5.5:
        verdict = "Leaning Hire / Needs Polish"
        summary = f"Has foundational knowledge for {role}, but answers lacked sufficient technical depth and structured problem-solving examples."
    else:
        verdict = "Not Ready / Needs Targeted Preparation"
        summary = f"Significant knowledge gaps identified in core {role} concepts. Dedicated study and hands-on project practice recommended."

    if not strengths:
        strengths.append("Willingness to take on challenging questions under simulated interview conditions.")
    if not improvements:
        improvements.append("Continue practicing with high-concurrency or edge-case design questions to reach senior/staff level.")

    return {
        "overall_score": avg_score,
        "verdict": verdict,
        "summary": summary,
        "scores": {
            "technical": round(sum(tech_scores) / len(tech_scores), 1),
            "problem_solving": round(sum(prob_scores) / len(prob_scores), 1),
            "communication": round(sum(comm_scores) / len(comm_scores), 1),
            "practical": round(sum(pract_scores) / len(pract_scores), 1)
        },
        "strengths": strengths[:4],
        "improvements": improvements[:4],
        "breakdown": breakdown
    }

def print_banner():
    print(f"{Colors.CYAN}{'='*68}")
    print(f"       SMART AI INTERVIEWER - ROLE-BASED PRACTICE & FEEDBACK")
    print(f"{'='*68}{Colors.RESET}")
    print(f"{Colors.DIM}Type 'end' at any prompt to stop the interview and generate feedback.{Colors.RESET}\n")

def display_feedback_report(feedback, role, level, report_filename=None):
    """Render a beautiful, structured feedback report in terminal and write to file."""
    score = feedback["overall_score"]
    
    # Score color
    if score >= 8.0:
        score_color = Colors.GREEN
    elif score >= 6.0:
        score_color = Colors.YELLOW
    else:
        score_color = Colors.RED
        
    print("\n" + f"{Colors.HEADER}{'='*68}")
    print(f"             CANDIDATE INTERVIEW EVALUATION REPORT")
    print(f"{'='*68}{Colors.RESET}\n")
    
    print(f"{Colors.BOLD}Target Role:{Colors.RESET} {role} ({level})")
    print(f"{Colors.BOLD}Overall Score:{Colors.RESET} {score_color}{Colors.BOLD}{score} / 10.0{Colors.RESET}")
    print(f"{Colors.BOLD}Assessment Verdict:{Colors.RESET} {score_color}{feedback['verdict']}{Colors.RESET}")
    print(f"{Colors.BOLD}Executive Summary:{Colors.RESET} {feedback['summary']}\n")
    
    # Pillar Scores
    print(f"{Colors.CYAN}{Colors.BOLD}--- Performance Pillar Scorecard ---{Colors.RESET}")
    pillars = feedback.get("scores", {})
    for pillar, val in pillars.items():
        bar = "#" * int(val) + "-" * (10 - int(val))
        print(f"  * {pillar.replace('_', ' ').title():<22} [{bar}] {val}/10")
    print()
    
    # Key Strengths
    print(f"{Colors.GREEN}{Colors.BOLD}--- Key Strengths Observed ---{Colors.RESET}")
    for item in feedback.get("strengths", []):
        print(f"  {Colors.GREEN}[+] {Colors.RESET}{item}")
    print()
    
    # Areas to Improve
    print(f"{Colors.YELLOW}{Colors.BOLD}--- Priority Improvement Areas ---{Colors.RESET}")
    for item in feedback.get("improvements", []):
        print(f"  {Colors.YELLOW}[!] {Colors.RESET}{item}")
    print()
    
    # Question Breakdown
    print(f"{Colors.CYAN}{Colors.BOLD}--- Question-by-Question Deep Dive ---{Colors.RESET}")
    for item in feedback.get("breakdown", []):
        q_score = item.get("score", 0)
        q_col = Colors.GREEN if q_score >= 7.5 else (Colors.YELLOW if q_score >= 5.0 else Colors.RED)
        print(f"\n{Colors.BOLD}Question {item.get('question_num', '')} [{item.get('category', 'Technical')}]{Colors.RESET} - Score: {q_col}{q_score}/10{Colors.RESET}")
        print(f"{Colors.DIM}Q: {item.get('question', '')}{Colors.RESET}")
        print(f"{Colors.BLUE}Your Answer:{Colors.RESET} {item.get('candidate_answer', '')}")
        print(f"{Colors.YELLOW}Analysis:{Colors.RESET} {item.get('feedback', '')}")
        if item.get("ideal_points"):
            print(f"{Colors.GREEN}Model Concept / Key Missing Elements:{Colors.RESET} {item.get('ideal_points')}")
            
    print("\n" + f"{Colors.HEADER}{'='*68}{Colors.RESET}")
    
    # Save to Markdown
    if report_filename:
        with open(report_filename, "w", encoding="utf-8") as f:
            f.write(f"# Interview Evaluation Report: {role} ({level})\n\n")
            f.write(f"- **Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Overall Score**: {score} / 10.0\n")
            f.write(f"- **Verdict**: {feedback['verdict']}\n")
            f.write(f"- **Summary**: {feedback['summary']}\n\n")
            
            f.write("## Pillar Scorecard\n\n")
            for p, v in pillars.items():
                f.write(f"- **{p.replace('_', ' ').title()}**: {v} / 10\n")
                
            f.write("\n## Key Strengths\n\n")
            for s in feedback.get("strengths", []):
                f.write(f"- {s}\n")
                
            f.write("\n## Where to Improve\n\n")
            for imp in feedback.get("improvements", []):
                f.write(f"- {imp}\n")
                
            f.write("\n## Detailed Question Breakdown\n\n")
            for b in feedback.get("breakdown", []):
                f.write(f"### Question {b.get('question_num')}: {b.get('category')}\n")
                f.write(f"**Question**: {b.get('question')}\n\n")
                f.write(f"**Your Answer**: {b.get('candidate_answer')}\n\n")
                f.write(f"**Score**: {b.get('score')} / 10\n\n")
                f.write(f"**Feedback**: {b.get('feedback')}\n\n")
                f.write(f"**Model Concept**: {b.get('ideal_points')}\n\n")
                f.write("---\n")
                
        print(f"{Colors.GREEN}Report saved to: {report_filename}{Colors.RESET}\n")

def run_interview():
    print_banner()
    
    # Role Selection
    print(f"{Colors.BOLD}Select or enter the role you want to be interviewed for:{Colors.RESET}")
    print("  1. Software Engineer (General / Backend)")
    print("  2. Frontend Developer (React, Web Performance, UI)")
    print("  3. Data Scientist (ML, Statistics, Evaluation)")
    print("  4. DevOps / Cloud Engineer (Kubernetes, CI/CD, Reliability)")
    print("  5. Product Manager (Strategy, Metrics, Prioritization)")
    print("  6. Custom Role (Type your own title)\n")
    
    role_choice = input(f"{Colors.CYAN}Enter choice (1-6) or role name: {Colors.RESET}").strip()
    
    role_map = {
        "1": "Software Engineer",
        "2": "Frontend Developer",
        "3": "Data Scientist",
        "4": "DevOps Engineer",
        "5": "Product Manager"
    }
    
    if role_choice in role_map:
        role = role_map[role_choice]
    elif role_choice == "6" or not role_choice:
        role = input(f"{Colors.CYAN}Enter custom role title (e.g. Machine Learning Engineer): {Colors.RESET}").strip()
        if not role:
            role = "Software Engineer"
    else:
        role = role_choice

    # Seniority Level
    print(f"\n{Colors.BOLD}Select seniority level:{Colors.RESET}")
    print("  1. Junior (0-2 years)")
    print("  2. Mid-Level (2-5 years)")
    print("  3. Senior / Lead (5+ years)")
    level_choice = input(f"{Colors.CYAN}Enter level (1-3, default 2): {Colors.RESET}").strip()
    level_map = {"1": "Junior", "2": "Mid-Level", "3": "Senior"}
    level = level_map.get(level_choice, "Mid-Level")
    
    # Check for optional API Key
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        # Prompt if user wants to enter one, or hit enter for smart built-in engine
        print(f"\n{Colors.DIM}(Optional) Press Enter to use the built-in Smart Evaluation Engine, or paste a Gemini API Key:{Colors.RESET}")
        custom_key = input(f"{Colors.DIM}API Key [Leave empty for built-in]: {Colors.RESET}").strip()
        if custom_key:
            api_key = custom_key
            
    print(f"\n{Colors.GREEN}[+] Initializing interview for: {role} ({level}){Colors.RESET}")
    if api_key:
        print(f"{Colors.GREEN}[+] Powered by Gemini 2.5 Flash LLM Engine{Colors.RESET}")
    else:
        print(f"{Colors.BLUE}[+] Powered by Built-in Intelligent Assessment Engine{Colors.RESET}")
        
    questions = generate_dynamic_questions(role, level, api_key)
    print(f"{Colors.GREEN}[+] Prepared {len(questions)} tailored interview questions.{Colors.RESET}")
    print(f"{Colors.YELLOW}Remember: You can type 'end' at any time to receive your feedback and report.{Colors.RESET}\n")
    print(f"{Colors.DIM}Press Enter to start the first question...{Colors.RESET}")
    input()
    
    interview_history = []
    
    for i, q_data in enumerate(questions, 1):
        print(f"{Colors.HEADER}====================================================================")
        print(f" QUESTION {i} OF {len(questions)} | Category: {q_data['category']}")
        print(f"===================================================================={Colors.RESET}")
        print(f"\n{Colors.BOLD}{q_data['question']}{Colors.RESET}\n")
        print(f"{Colors.DIM}[Type your answer below. Type 'end' to finish interview and get feedback]{Colors.RESET}")
        
        # Read multi-line or single-line response
        lines = []
        try:
            line = input(f"{Colors.BLUE}> {Colors.RESET}")
            if line.strip().lower() == "end":
                print(f"\n{Colors.YELLOW}Interview concluded by candidate. Generating feedback...{Colors.RESET}")
                break
            lines.append(line)
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}Interview stopped. Generating feedback...{Colors.RESET}")
            break
            
        candidate_answer = " ".join(lines).strip()
        
        if not candidate_answer:
            candidate_answer = "(No answer provided)"
            
        interview_history.append({
            "category": q_data["category"],
            "question": q_data["question"],
            "answer": candidate_answer,
            "keywords": q_data.get("keywords", []),
            "model_answer": q_data.get("model_answer", "")
        })
        
        print(f"{Colors.GREEN}[+] Answer recorded.{Colors.RESET}\n")
        time.sleep(0.5)

    # Analyze & Produce Feedback
    print(f"\n{Colors.CYAN}Analyzing your responses against industry benchmarks for {role}...{Colors.RESET}")
    feedback = evaluate_interview(role, level, interview_history, api_key)
    
    report_filename = f"interview_feedback_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    display_feedback_report(feedback, role, level, report_filename)

if __name__ == "__main__":
    try:
        run_interview()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Session cancelled by user.{Colors.RESET}")
        sys.exit(0)
