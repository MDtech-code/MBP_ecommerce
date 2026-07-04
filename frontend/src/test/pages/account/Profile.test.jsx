// src/test/pages/account/Profile.test.jsx

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import Profile from "../../../pages/account/Profile";

// ─────────────────────────────────────────────────────────────
// Mock Zustand
// ─────────────────────────────────────────────────────────────

let mockUser = {
  id: 1,
  email: "john@test.com",
  profile: {
    avatar: "/avatar.jpg",
    phone: "03001234567",
  },
};

vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) =>
    selector({
      user: mockUser,
    }),
}));

// ─────────────────────────────────────────────────────────────
// Mock useProfile
// ─────────────────────────────────────────────────────────────

const useProfile = vi.fn();

vi.mock(
  "../../../hooks/account/useAuthMutations",
  () => ({
    useProfile: (...args) => useProfile(...args),
  }),
);

// ─────────────────────────────────────────────────────────────
// Mock hasAuthToken
// ─────────────────────────────────────────────────────────────

const { hasAuthToken } = vi.hoisted(() => ({
  hasAuthToken: vi.fn(),
}));

vi.mock("../../../api/auth", () => ({
  hasAuthToken: vi.fn(),
}));

// ─────────────────────────────────────────────────────────────
// Mock DashboardLayout
// ─────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/DashboardLayout",
  () => ({
    default: ({ children }) => (
      <div data-testid="dashboard-layout">
        {children}
      </div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────
// Mock ProfileView
// ─────────────────────────────────────────────────────────────

const profileView = vi.fn();

vi.mock(
  "../../../components/account/profile/ProfileView",
  () => ({
    default: (props) => {
      profileView(props);

      return (
        <div data-testid="profile-view">
          Profile View
        </div>
      );
    },
  }),
);

// ─────────────────────────────────────────────────────────────
// Mock ProfileEditForm
// ─────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/profile/ProfileEditForm",
  () => ({
    default: () => (
      <div data-testid="profile-edit">
        Edit Form
      </div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────
// Mock AvatarModal
// ─────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/profile/AvatarModal",
  () => ({
    default: () => (
      <div data-testid="avatar-modal">
        Avatar Modal
      </div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hasAuthToken.mockReturnValue(true);

  useProfile.mockReturnValue({
    isLoading: false,
  });

  mockUser = {
    id: 1,
    email: "john@test.com",
    profile: {
      avatar: "/avatar.jpg",
      phone: "03001234567",
    },
  };
});

// ─────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────

describe("Profile Page", () => {
  it("renders dashboard layout", () => {
    render(<Profile />);

    expect(
      screen.getByTestId("dashboard-layout"),
    ).toBeInTheDocument();
  });

  it("calls useProfile", () => {
    render(<Profile />);

    expect(useProfile).toHaveBeenCalledTimes(1);
  });

  it("passes enabled option to useProfile", () => {
    render(<Profile />);

    expect(useProfile).toHaveBeenCalledWith({
      enabled: true,
    });
  });

  it("renders loading spinner while loading and user is missing", () => {
    mockUser = null;

    useProfile.mockReturnValue({
      isLoading: true,
    });

    const { container } = render(<Profile />);

    expect(
      container.querySelector(".loading-spinner"),
    ).toBeTruthy();
  });

  it("renders ProfileView after loading", () => {
    render(<Profile />);

    expect(
      screen.getByTestId("profile-view"),
    ).toBeInTheDocument();
  });

  it("passes user into ProfileView", () => {
    render(<Profile />);

    expect(profileView).toHaveBeenCalled();

    expect(
      profileView.mock.calls[0][0].user.email,
    ).toBe("john@test.com");
  });

  it("does not render edit form initially", () => {
    render(<Profile />);

    expect(
      screen.queryByTestId("profile-edit"),
    ).not.toBeInTheDocument();
  });

  it("does not show avatar modal initially", () => {
    render(<Profile />);

    expect(
      screen.queryByTestId("avatar-modal"),
    ).not.toBeInTheDocument();
  });

  it("passes onEdit callback to ProfileView", () => {
    render(<Profile />);

    expect(
      typeof profileView.mock.calls[0][0].onEdit,
    ).toBe("function");
  });

  it("passes onAvatarClick callback to ProfileView", () => {
    render(<Profile />);

    expect(
      typeof profileView.mock.calls[0][0]
        .onAvatarClick,
    ).toBe("function");
  });

  it("passes avatar to AvatarModal after callback", () => {
    render(<Profile />);

    const callback =
      profileView.mock.calls[0][0].onAvatarClick;

    callback();

    expect(
      screen.getByTestId("avatar-modal"),
    ).toBeInTheDocument();
  });

  it("passes current avatar correctly", () => {
    render(<Profile />);

    expect(
      profileView.mock.calls[0][0].user.profile.avatar,
    ).toBe("/avatar.jpg");
  });
});