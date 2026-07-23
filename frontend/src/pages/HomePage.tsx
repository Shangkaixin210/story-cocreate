import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { apiFetch } from "../api/client";
import Button from "../components/Shared/Button";
import Onboarding from "../components/Shared/Onboarding";
import "./HomePage.css";

const CHANNEL_LABEL: Record<string, string> = {
  "4-7": " 幼儿通道 4-7岁",
  "8-12": " 学龄通道 8-12岁",
};

export default function HomePage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [showOnboarding, setShowOnboarding] = useState(
    () => sessionStorage.getItem("ai_bole_show_onboarding") === "true",
  );

  function handleOnboardingFinish() {
    sessionStorage.removeItem("ai_bole_show_onboarding");
    setShowOnboarding(false);
  }

  async function switchChannel(age: "4-7" | "8-12") {
    if (!user || user.age_group === age) return;
    try {
      await apiFetch(`/auth/me/channel?age_group=${age}`, { method: "PATCH" });
    } catch {}
    setUser({ ...user, age_group: age });
  }

  return (
    <div className="home-page">
      {showOnboarding && <Onboarding onFinish={handleOnboardingFinish} />}
      <div className="home-hero">
        <span className="home-emoji animate-float">🌟</span>
        <h1 className="home-title animate-fade-in">
          欢迎来到
          <br />
          故事共创世界！
        </h1>
        <p className="home-subtitle animate-slide-up">
          {user
            ? `你好，${user.display_name || user.username}！`
            : "和故事导演一起，创造属于你的精彩故事吧~"}
        </p>
        {user?.age_group && (
          <div className="home-channel">
            <span className="home-channel-label">
              {CHANNEL_LABEL[user.age_group] || user.age_group}
            </span>
            <button
              className="home-channel-switch"
              onClick={() =>
                switchChannel(user.age_group === "4-7" ? "8-12" : "4-7")
              }
            >
              切换
            </button>
          </div>
        )}
      </div>

      <div className="home-actions animate-slide-up">
        <Button
          variant="primary"
          size="lg"
          onClick={() => navigate("/characters")}
        >
          创建角色，开始冒险
        </Button>
        <Button
          variant="secondary"
          size="lg"
          onClick={() => navigate("/gallery")}
        >
          看看我的故事
        </Button>
      </div>
    </div>
  );
}
