import React, { useState, useEffect } from "react";
import { Header } from "./components/Header";
import { SessionList } from "./components/SessionList";
import { CreateSessionModal } from "./components/CreateSessionModal";
import { InspectionWorkspace } from "./components/InspectionWorkspace";
import { InspectionSession } from "./types/inspection";
import { fetchSessions, fetchSession } from "./services/api";

export const App: React.FC = () => {
  const [sessions, setSessions] = useState<InspectionSession[]>([]);
  const [activeSession, setActiveSession] = useState<InspectionSession | null>(null);
  const [isNewSessionOpen, setIsNewSessionOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadSessions = async () => {
    try {
      setLoading(true);
      const data = await fetchSessions();
      setSessions(data);
    } catch (err: any) {
      console.error("Failed to load sessions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleSelectSession = async (session: InspectionSession) => {
    try {
      const fullSession = await fetchSession(session.id);
      setActiveSession(fullSession);
    } catch (err: any) {
      console.error(err);
      setActiveSession(session);
    }
  };

  const handleSessionCreated = (newSession: InspectionSession) => {
    setSessions((prev) => [newSession, ...prev]);
    setActiveSession(newSession);
  };

  const handleSessionUpdated = (updated: InspectionSession) => {
    setActiveSession(updated);
    setSessions((prev) =>
      prev.map((s) => (s.id === updated.id ? updated : s))
    );
  };

  return (
    <div className="app-container">
      <Header
        onNewSession={() => setIsNewSessionOpen(true)}
        onRefresh={() => {
          loadSessions();
          if (activeSession) {
            handleSelectSession(activeSession);
          }
        }}
        onBackToSessions={() => setActiveSession(null)}
        activeSessionTitle={activeSession?.title}
      />

      <main className="main-content">
        {activeSession ? (
          <InspectionWorkspace
            session={activeSession}
            onSessionUpdated={handleSessionUpdated}
          />
        ) : (
          <SessionList
            sessions={sessions}
            onSelectSession={handleSelectSession}
            onNewSession={() => setIsNewSessionOpen(true)}
            loading={loading}
          />
        )}
      </main>

      <CreateSessionModal
        isOpen={isNewSessionOpen}
        onClose={() => setIsNewSessionOpen(false)}
        onSessionCreated={handleSessionCreated}
      />
    </div>
  );
};

export default App;
