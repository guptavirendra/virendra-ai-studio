import { useEffect, useState } from 'react';

interface ContentStats {
  topic: string;
  status: string;
  approved: boolean;
  published: boolean;
}

function App() {
  const [items, setItems] = useState<ContentStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then(() => setLoading(false))
      .catch(() => setLoading(false));
  }, []);

  return (
    <div className="app-shell">
      <header>
        <h1>Virendra AI Studio</h1>
        <p>Dashboard preview for content automation.</p>
      </header>

      <main>
        {loading ? (
          <div className="status">Loading…</div>
        ) : (
          <div className="status">Ready to connect with FastAPI backend.</div>
        )}

        <section className="panels">
          <article className="panel">
            <h2>Next Actions</h2>
            <ul>
              <li>Trend detection</li>
              <li>Script generation</li>
              <li>Thumbnail creation</li>
              <li>Publish review</li>
            </ul>
          </article>

          <article className="panel">
            <h2>Mock Content Status</h2>
            <ul>
              {items.length === 0 ? (
                <li>No content items yet.</li>
              ) : (
                items.map((item) => (
                  <li key={item.topic}>
                    {item.topic} — {item.status}
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
