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
          <li>Your name and work email, so you can sign in.</li>
          <li>Your location, grade and employment type, only to pick which policies apply to you.</li>
          <li>Your leave balances, as uploaded by HR.</li>
          <li>Requests you send to HR and their replies (encrypted, deleted some months after they're closed).</li>
          {me.is_interviewer && <li>The interviews you're assigned to, and whether candidates attended.</li>}
        </ul>
        <h2>What isn't kept</h2>
        <ul className="p-list">
          <li>The wording of your Ask HR chats. Only a record that you asked something, and what kind of answer it got, is kept.</li>
          <li>Anything typed on the sensitive-topic screen.</li>
        </ul>
        <p className="small muted">
          If your organisation has switched on an AI model, your question is sent to it with phone numbers, emails,
          PAN and Aadhaar numbers masked. This portal shows you only your own information. Everything is stored on
          your organisation's own server. To correct or delete your data, ask your HR team.
        </p>
      </section>
      <button className="btn" onClick={onSignOut}>Sign out</button>
    </div>
  );
}
