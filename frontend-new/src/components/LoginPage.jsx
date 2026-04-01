import { useState } from "react";

/**
 * LoginPage - Página de login/registro estilo Instagram (tema azul)
 *
 * Features:
 * - Tabs para alternar entre Login e Registro
 * - Validação de formulário
 * - Feedback visual de loading/erro
 * - Tema azul profissional (#0095f6)
 */
export function LoginPage({ onLoginSuccess, onClose }) {
  const [activeTab, setActiveTab] = useState("login"); // 'login' | 'register'
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (activeTab === "login") {
        // LOGIN
        const response = await fetch("http://localhost:5001/api/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });

        const data = await response.json();

        if (data.success && data.token) {
          // Salvar no localStorage
          localStorage.setItem("token", data.token);
          localStorage.setItem("user", JSON.stringify(data.user));
          localStorage.setItem("userRole", data.user?.role || "operator");
          localStorage.setItem("userName", data.user?.full_name || data.user?.email || "Admin");

          // Callback de sucesso
          if (onLoginSuccess) {
            onLoginSuccess({
              token: data.token,
              user: data.user,
            });
          }
        } else {
          setError(data.error || "Email ou senha incorretos");
        }
      } else {
        // REGISTRO
        const response = await fetch("http://localhost:5001/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email,
            password,
            full_name: fullName,
            company_name: companyName,
          }),
        });

        const data = await response.json();

        if (data.success) {
          // Auto-login após registro
          setActiveTab("login");
          setPassword("");
          setError("");
          alert("Conta criada com sucesso! Faça login para continuar.");
        } else {
          setError(data.error || "Erro ao criar conta");
        }
      }
    } catch (err) {
      console.error("Login/Register error:", err);
      setError("Erro de conexão. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0, 0, 0, 0.5)",
        backdropFilter: "blur(4px)",
      }}
      onClick={(e) => {
        // Fechar ao clicar fora (opcional)
        if (e.target === e.currentTarget && onClose) {
          onClose();
        }
      }}
    >
      <div
        style={{
          background: "#fff",
          borderRadius: 8,
          width: "90%",
          maxWidth: 400,
          overflow: "hidden",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header com logo e título */}
        <div style={{ padding: "40px 40px 20px", textAlign: "center" }}>
          <div
            style={{
              width: 80,
              height: 80,
              margin: "0 auto 20px",
              background: "linear-gradient(135deg, #0095f6 0%, #0056b3 100%)",
              borderRadius: 20,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#fff",
              fontSize: 32,
            }}
          >
            🎥
          </div>
          <h2
            style={{
              fontSize: 24,
              fontWeight: 600,
              color: "#262626",
              marginBottom: 8,
            }}
          >
            EPI Monitor
          </h2>
          <p
            style={{
              fontSize: 14,
              color: "#8e8e8e",
              margin: 0,
            }}
          >
            Sistema de Reconhecimento de EPI com YOLO
          </p>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            borderBottom: "1px solid #dbdbdb",
            margin: "0 40px",
          }}
        >
          <button
            onClick={() => {
              setActiveTab("login");
              setError("");
            }}
            style={{
              flex: 1,
              padding: "12px 0",
              background: "none",
              border: "none",
              borderBottom: activeTab === "login" ? "2px solid #0095f6" : "none",
              color: activeTab === "login" ? "#262626" : "#8e8e8e",
              fontWeight: activeTab === "login" ? 600 : 400,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Entrar
          </button>
          <button
            onClick={() => {
              setActiveTab("register");
              setError("");
            }}
            style={{
              flex: 1,
              padding: "12px 0",
              background: "none",
              border: "none",
              borderBottom: activeTab === "register" ? "2px solid #0095f6" : "none",
              color: activeTab === "register" ? "#262626" : "#8e8e8e",
              fontWeight: activeTab === "register" ? 600 : 400,
              fontSize: 14,
              cursor: "pointer",
            }}
          >
            Cadastrar
          </button>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          style={{
            padding: "20px 40px 40px",
          }}
        >
          {error && (
            <div
              style={{
                background: "#fee",
                color: "#c33",
                padding: "10px 12px",
                borderRadius: 4,
                fontSize: 13,
                marginBottom: 16,
                border: "1px solid #fcc",
              }}
            >
              {error}
            </div>
          )}

          {activeTab === "register" && (
            <>
              <div style={{ marginBottom: 12 }}>
                <input
                  type="text"
                  placeholder="Nome completo"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    border: "1px solid #dbdbdb",
                    borderRadius: 4,
                    fontSize: 14,
                    background: "#fafafa",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div style={{ marginBottom: 12 }}>
                <input
                  type="text"
                  placeholder="Nome da empresa"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    border: "1px solid #dbdbdb",
                    borderRadius: 4,
                    fontSize: 14,
                    background: "#fafafa",
                    boxSizing: "border-box",
                  }}
                />
              </div>
            </>
          )}

          <div style={{ marginBottom: 12 }}>
            <input
              type="email"
              placeholder="Email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid #dbdbdb",
                borderRadius: 4,
                fontSize: 14,
                background: "#fafafa",
                boxSizing: "border-box",
              }}
            />
          </div>

          <div style={{ marginBottom: 20 }}>
            <input
              type="password"
              placeholder="Senha"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              style={{
                width: "100%",
                padding: "10px 12px",
                border: "1px solid #dbdbdb",
                borderRadius: 4,
                fontSize: 14,
                background: "#fafafa",
                boxSizing: "border-box",
              }}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "10px",
              background: loading ? "#b2dffc" : "#0095f6",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              fontSize: 14,
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Processando..." : activeTab === "login" ? "Entrar" : "Cadastrar"}
          </button>

          {activeTab === "login" && (
            <div
              style={{
                marginTop: 20,
                textAlign: "center",
                fontSize: 13,
                color: "#8e8e8e",
              }}
            >
              Esqueceu sua senha?{" "}
              <a
                href="#"
                style={{
                  color: "#00376b",
                  textDecoration: "none",
                  fontWeight: 600,
                }}
                onClick={(e) => {
                  e.preventDefault();
                  alert("Funcionalidade de recuperação de senha em desenvolvimento.");
                }}
              >
                Recuperar
              </a>
            </div>
          )}
        </form>

        {/* Footer */}
        <div
          style={{
            padding: "20px 40px",
            background: "#fafafa",
            borderTop: "1px solid #dbdbdb",
            textAlign: "center",
            fontSize: 14,
            color: "#262626",
          }}
        >
          {activeTab === "login" ? (
            <>
              Não tem uma conta?{" "}
              <button
                onClick={() => {
                  setActiveTab("register");
                  setError("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#0095f6",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                Cadastre-se
              </button>
            </>
          ) : (
            <>
              Já tem uma conta?{" "}
              <button
                onClick={() => {
                  setActiveTab("login");
                  setError("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#0095f6",
                  fontWeight: 600,
                  cursor: "pointer",
                  fontSize: 14,
                }}
              >
                Entrar
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
