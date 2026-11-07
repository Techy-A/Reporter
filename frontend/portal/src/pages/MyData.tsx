import type { Me } from "../main";

export default function MyData({ me, onSignOut }: { me: Me; onSignOut: () => void }) {
  return (
    <div className="p-page">
      <h1>My data</h1>
      <section className="p-card">
        <dl className="p-facts">
          <div><dt>Name</dt><dd>{me.name}</dd></div>
          <div><dt>Email</dt><dd>{me.email}</dd></div>
          <div><dt>Organisation</dt><dd>{me.organisation}</dd></div>
        </dl>
      </section>
      <section className="p-card">
        <h2>What Reporter uses about you</h2>
        <ul className="p-list">
          <li>Your name and work email, so you can sign in and be assigned interviews.</li>
          <li>The interviews you're assigned to, and whether candidates attended.</li>
        </ul>
        <p className="small muted">
          This portal shows you only your own information. Candidates' phone numbers and emails are never shown here.
          Everything is stored on your organisation's own server. To correct or delete your data, ask your HR team.
        </p>
      </section>
      <button className="btn" onClick={onSignOut}>Sign out</button>
    </div>
  );
}
