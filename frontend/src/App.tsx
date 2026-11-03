import { useEffect, useState } from 'react';

interface ContentStats {
  id: number;
  topic: string;
  status: string;
  approved: boolean;
  published: boolean;
  source?: string;
  video_path?: string | null;
}

interface CurrentUser {
  id: number;
  username: string;
  role: 'admin' | 'member';
  is_active: boolean;
}

type ManagedUser = CurrentUser;

interface SummaryStats {
  total: number;
  draft: number;
  approved: number;
  published: number;
  review_queue: number;
}

interface ReviewItem extends ContentStats {
  publish_target?: string;
}

interface FormState {
  topic: string;
  source: string;
  confidence: number;
  competition: string;
  estimated_views: string;
}

function App() {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [csrfToken, setCsrfToken] = useState('');
  const [sessionChecked, setSessionChecked] = useState(false);
  const [items, setItems] = useState<ContentStats[]>([]);
  const [reviewQueue, setReviewQueue] = useState<ReviewItem[]>([]);
  const [summary, setSummary] = useState<SummaryStats>({
    total: 0,
    draft: 0,
    approved: 0,
    published: 0,
    review_queue: 0,
  });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [workingId, setWorkingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [authError, setAuthError] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'member'>('member');
  const [managedUsers, setManagedUsers] = useState<ManagedUser[]>([]);
  const [passwordResets, setPasswordResets] = useState<Record<number, string>>({});
  const [userMessage, setUserMessage] = useState('');
  const [form, setForm] = useState<FormState>({
    topic: '',
    source: 'government',
    confidence: 7,
    competition: 'low',
    estimated_views: 'high',
  });

  const apiFetch = (input: RequestInfo | URL, init: RequestInit = {}) => {
    const headers = new Headers(init.headers);
    if (csrfToken) headers.set('X-CSRF-Token', csrfToken);
    return fetch(input, { ...init, headers, credentials: 'same-origin' });
  };

  const refreshDashboard = async () => {
    const [itemsRes, reviewRes, summaryRes] = await Promise.all([
      apiFetch('/content'),
      apiFetch('/content/review'),
      apiFetch('/content/summary'),
    ]);
    if (![itemsRes, reviewRes, summaryRes].every((response) => response.ok)) {
      throw new Error('Unable to load dashboard data');
    }

    const itemsData = await itemsRes.json();
    const reviewData = await reviewRes.json();
    const summaryData = await summaryRes.json();

    setItems(itemsData);
    setReviewQueue(reviewData);
    setSummary(summaryData);
  };

  const refreshManagedUsers = async () => {
    const response = await apiFetch('/auth/users');
    if (!response.ok) throw new Error('Unable to load team accounts');
    setManagedUsers(await response.json());
  };

  useEffect(() => {
    fetch('/auth/me', { credentials: 'same-origin' })
      .then(async (response) => {
        if (!response.ok) return;
        const session = await response.json();
        setUser(session.user);
        setCsrfToken(session.csrf_token);
        await refreshDashboard();
        if (session.user.role === 'admin') await refreshManagedUsers();
      })
      .catch(() => setAuthError('Unable to check your sign-in session'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!loading) setSessionChecked(true);
  }, [loading]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthError('');
    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({ username, password }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Sign-in failed');
      setUser(payload.user);
      setCsrfToken(payload.csrf_token);
      setPassword('');
      await refreshDashboard();
      if (payload.user.role === 'admin') await refreshManagedUsers();
    } catch (loginError) {
      setAuthError(loginError instanceof Error ? loginError.message : 'Sign-in failed');
    }
  };

  const handleLogout = async () => {
    await apiFetch('/auth/logout', { method: 'POST' });
    setUser(null);
    setCsrfToken('');
    setItems([]);
    setReviewQueue([]);
  };

  const handleCreateUser = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setUserMessage('');
    setError('');
    try {
      const response = await apiFetch('/auth/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: newUsername, password: newPassword, role: newRole }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to create user');
      setNewUsername('');
      setNewPassword('');
      setUserMessage(`Created ${payload.role} account: ${payload.username}`);
      await refreshManagedUsers();
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Unable to create user');
    }
  };

  const handleToggleUser = async (target: ManagedUser) => {
    setError('');
    setUserMessage('');
    try {
      const response = await apiFetch(`/auth/users/${target.id}/active`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_active: !target.is_active }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to update account');
      setUserMessage(`${target.username} is now ${payload.is_active ? 'active' : 'disabled'}. Their sessions have been revoked.`);
      await refreshManagedUsers();
    } catch (accountError) {
      setError(accountError instanceof Error ? accountError.message : 'Unable to update account');
    }
  };

  const handleResetUserPassword = async (
    event: React.FormEvent<HTMLFormElement>,
    target: ManagedUser,
  ) => {
    event.preventDefault();
    setError('');
    setUserMessage('');
    try {
      const response = await apiFetch(`/auth/users/${target.id}/password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: passwordResets[target.id] }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || 'Unable to reset password');
      setPasswordResets((current) => ({ ...current, [target.id]: '' }));
      if (target.id === user?.id) {
        setUser(null);
        setCsrfToken('');
        setUsername(target.username);
        setAuthError('Password changed. Sign in again with your new password.');
        return;
      }
      setUserMessage(`Password reset for ${target.username}; all their sessions have been revoked.`);
    } catch (passwordError) {
      setError(passwordError instanceof Error ? passwordError.message : 'Unable to reset password');
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setError('');

    try {
      const response = await apiFetch('/content/create-with-ai', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          confidence: Number(form.confidence),
        }),
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Unable to create content');
      }

      setForm({
        topic: '',
        source: 'government',
        confidence: 7,
        competition: 'low',
        estimated_views: 'high',
      });
      await refreshDashboard();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Something went wrong');
    } finally {
      setCreating(false);
    }
  };

  const handleApprove = async (itemId: number) => {
    setWorkingId(itemId);
    setError('');

    try {
      const response = await apiFetch(`/content/${itemId}/approve`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Approval failed');
      }
      await refreshDashboard();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Approval failed');
    } finally {
      setWorkingId(null);
    }
  };

  const handleRender = async (itemId: number) => {
    setWorkingId(itemId);
    setError('');

    try {
      const response = await apiFetch(`/content/${itemId}/render-video`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Video render failed');
      }
      await refreshDashboard();
    } catch (renderError) {
      setError(renderError instanceof Error ? renderError.message : 'Video render failed');
    } finally {
      setWorkingId(null);
    }
  };

  const handleYouTubeUpload = async (item: ContentStats) => {
    if (!item.video_path) return;
    setWorkingId(item.id);
    setError('');

    try {
      const response = await apiFetch(`/content/${item.id}/upload-youtube`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: item.video_path, privacy_status: 'private' }),
      });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'YouTube upload failed');
      }
      await refreshDashboard();
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'YouTube upload failed');
    } finally {
      setWorkingId(null);
    }
  };

  const handleInstagramPublish = async (itemId: number) => {
    setWorkingId(itemId);
    setError('');

    try {
      const response = await apiFetch(`/content/${itemId}/publish/instagram`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Instagram publish failed');
      }
      await refreshDashboard();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Instagram publish failed');
    } finally {
      setWorkingId(null);
    }
  };

  const handleFacebookPublish = async (itemId: number) => {
    setWorkingId(itemId);
    setError('');

    try {
      const response = await apiFetch(`/content/${itemId}/publish/facebook`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Facebook publish failed');
      }
      await refreshDashboard();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Facebook publish failed');
    } finally {
      setWorkingId(null);
    }
  };

  const handleTelegramPublish = async (itemId: number) => {
    setWorkingId(itemId);
    setError('');

    try {
      const response = await apiFetch(`/content/${itemId}/publish/telegram`, { method: 'POST' });
      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || 'Telegram publish failed');
      }
      await refreshDashboard();
    } catch (publishError) {
      setError(publishError instanceof Error ? publishError.message : 'Telegram publish failed');
    } finally {
      setWorkingId(null);
    }
  };

  if (!sessionChecked) {
    return <div className="app-shell"><main><div className="status">Checking sign-in…</div></main></div>;
  }

  if (!user) {
    return (
      <div className="app-shell">
        <header><h1>Virendra AI Studio</h1><p>Sign in to your content workspace.</p></header>
        <main>
          <section className="panel">
            <h2>Sign in</h2>
            <form className="content-form" onSubmit={handleLogin}>
              <label>Username<input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
              <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
              {authError ? <div className="error">{authError}</div> : null}
              <button type="submit">Sign in</button>
            </form>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header>
        <h1>Virendra AI Studio</h1>
        <p>Signed in as {user.username} ({user.role}) <button type="button" className="secondary" onClick={handleLogout}>Sign out</button></p>
      </header>

      <main>
        {loading ? (
          <div className="status">Loading…</div>
        ) : (
          <div className="status">Live content dashboard connected to FastAPI.</div>
        )}

        <section className="panels">
          {user.role === 'admin' ? (
            <article className="panel">
              <h2>Create user</h2>
              <form className="content-form" onSubmit={handleCreateUser}>
                <label>Username<input autoComplete="off" value={newUsername} onChange={(event) => setNewUsername(event.target.value)} required /></label>
                <label>Temporary password<input type="password" autoComplete="new-password" minLength={12} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></label>
                <label>Role<select value={newRole} onChange={(event) => setNewRole(event.target.value as 'admin' | 'member')}><option value="member">Member</option><option value="admin">Admin</option></select></label>
                {userMessage ? <div className="status">{userMessage}</div> : null}
                <button type="submit">Create account</button>
              </form>
            </article>
          ) : null}
          {user.role === 'admin' ? (
            <article className="panel">
              <h2>Manage accounts</h2>
              {error ? <div className="error">{error}</div> : null}
              {userMessage ? <div className="status">{userMessage}</div> : null}
              <ul className="account-list">
                {managedUsers.map((managedUser) => (
                  <li className="account-item" key={managedUser.id}>
                    <div className="account-heading">
                      <strong>{managedUser.username}</strong>
                      <span>{managedUser.role} · {managedUser.is_active ? 'Active' : 'Disabled'}</span>
                    </div>
                    <div className="account-controls">
                      {managedUser.id !== user.id ? (
                        <button type="button" className="secondary" onClick={() => handleToggleUser(managedUser)}>
                          {managedUser.is_active ? 'Disable account' : 'Reactivate account'}
                        </button>
                      ) : null}
                      <form onSubmit={(event) => handleResetUserPassword(event, managedUser)}>
                        <input
                          type="password"
                          autoComplete="new-password"
                          minLength={12}
                          maxLength={128}
                          aria-label={`New password for ${managedUser.username}`}
                          placeholder="New password (12+ characters)"
                          value={passwordResets[managedUser.id] || ''}
                          onChange={(event) => setPasswordResets((current) => ({
                            ...current,
                            [managedUser.id]: event.target.value,
                          }))}
                          required
                        />
                        <button type="submit">Reset password</button>
                      </form>
                    </div>
                  </li>
                ))}
              </ul>
            </article>
          ) : null}
          <article className="panel">
            <h2>Pipeline Overview</h2>
            <ul>
              <li>Total: {summary.total}</li>
              <li>Draft: {summary.draft}</li>
              <li>Approved: {summary.approved}</li>
              <li>Published: {summary.published}</li>
              <li>Review Queue: {summary.review_queue}</li>
            </ul>
          </article>

          <article className="panel">
            <h2>Create content</h2>
            <form className="content-form" onSubmit={handleSubmit}>
              <label>
                Topic
                <input
                  value={form.topic}
                  onChange={(event) => setForm((current) => ({ ...current, topic: event.target.value }))}
                  placeholder="AI tools for creators"
                  required
                />
              </label>

              <label>
                Source
                <select
                  value={form.source}
                  onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
                >
                  <option value="government">Government</option>
                  <option value="news">News</option>
                  <option value="business">Business</option>
                  <option value="trending">Trending</option>
                </select>
              </label>

              <label>
                Confidence
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={form.confidence}
                  onChange={(event) => setForm((current) => ({ ...current, confidence: Number(event.target.value) }))}
                />
              </label>

              <label>
                Competition
                <select
                  value={form.competition}
                  onChange={(event) => setForm((current) => ({ ...current, competition: event.target.value }))}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>

              <label>
                Estimated views
                <select
                  value={form.estimated_views}
                  onChange={(event) => setForm((current) => ({ ...current, estimated_views: event.target.value }))}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>

              {error ? <div className="error">{error}</div> : null}

              <button type="submit" disabled={creating || !form.topic.trim()}>
                {creating ? 'Creating…' : 'Create content'}
              </button>
            </form>
          </article>

          <article className="panel">
            <h2>Review Queue</h2>
            <ul className="action-list">
              {reviewQueue.length === 0 ? (
                <li>No content waiting for review.</li>
              ) : (
                reviewQueue.map((item) => (
                  <li key={item.id} className="action-item">
                    <div>
                      <strong>{item.topic}</strong>
                      <span>{item.status}</span>
                    </div>
                    <div className="button-row">
                      <button type="button" onClick={() => handleApprove(item.id)} disabled={workingId === item.id}>
                        {workingId === item.id ? 'Working…' : 'Approve'}
                      </button>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </article>

          <article className="panel">
            <h2>Recent Content</h2>
            <ul>
              {items.length === 0 ? (
                <li>No content items yet.</li>
              ) : (
                items.map((item) => (
                  <li key={item.id} className="action-item">
                    <div>
                      <strong>{item.topic}</strong>
                      <span>{item.video_path ? 'Video ready' : item.status}</span>
                    </div>
                    <div className="button-row">
                      <button type="button" onClick={() => handleRender(item.id)} disabled={workingId === item.id}>
                        {workingId === item.id ? 'Rendering…' : item.video_path ? 'Render again' : 'Render MP4'}
                      </button>
                      {!item.approved ? (
                        <button type="button" className="secondary" onClick={() => handleApprove(item.id)} disabled={workingId === item.id}>
                          Approve
                        </button>
                      ) : null}
                      {item.video_path ? (
                        <>
                          <a className="download-link" href={`/content/${item.id}/video`} download>
                            Download MP4
                          </a>
                          <a className="download-link" href={`/content/${item.id}/subtitles`} download>
                            Download SRT
                          </a>
                          {item.approved ? (
                            <>
                              <button type="button" className="secondary" onClick={() => handleYouTubeUpload(item)} disabled={workingId === item.id}>
                                Upload privately
                              </button>
                              <button type="button" className="secondary" onClick={() => handleInstagramPublish(item.id)} disabled={workingId === item.id}>
                                Publish Instagram Reel
                              </button>
                              <button type="button" className="secondary" onClick={() => handleFacebookPublish(item.id)} disabled={workingId === item.id}>
                                Publish Facebook video
                              </button>
                              <button type="button" className="secondary" onClick={() => handleTelegramPublish(item.id)} disabled={workingId === item.id}>
                                Publish on Telegram
                              </button>
                            </>
                          ) : (
                            <span>Approve before upload</span>
                          )}
                        </>
                      ) : null}
                    </div>
                  </li>
                ))
              )}
            </ul>
          </article>
        </section>
      </main>
    </div>
  );
}

export default App;
