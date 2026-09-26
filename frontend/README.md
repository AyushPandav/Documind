# DocuMind Mobile App

**Document Intelligence, Cited.**

DocuMind is an AI-native document intelligence RAG mobile application built with **React Native**, **Expo Router**, and **TypeScript**. It is designed specifically for high-impact judge demonstrations showcasing the core **document → chat → citation → source inspection** workflow.

---

## 📱 Core Features & Demonstration Flow

1. **Authentication Flow (`/auth/login` & `/auth/signup`)**:
   - Technical dark interface with cyan accents and monospace branding.
   - Inline email and password validation with reactive feedback.
   - Instant switching between login and signup without reloading the application.
   - Pre-populated credentials for instant judge demonstration.

2. **Main Document + RAG Workspace (`/app`)**:
   - Compact technical header with custom `DocuMindLogo` and quick-access drawer triggers.
   - **Knowledge Base Drawer (`DocumentsSheet`)**:
     - Native mobile dashed upload area with `expo-document-picker` support (PDF, PNG, JPG).
     - Full state progression: `QUEUED` ➔ `OCR` (purple pulsing) ➔ `PROCESSING` (cyan pulsing) ➔ `INDEXED` (solid cyan).
     - Live simulated progress bar with ASCII meter (`████████░░ 72%`).
     - Tappable document rows with context filtering (`Context: policy.pdf [✕]`).
   - **Chat & Citations**:
     - Distinct User vs Assistant glassmorphism styling.
     - Inline clickable citations (`[1]`, `[2]`).
     - Interactive press animation on citation chips.
     - Sequential bouncing dot loading animation (`● ● ●`).
     - Distinct **Insufficient Information** state with amber warning banner when questions cannot be answered from uploaded corpus.
   - **Source Inspection Sheet (`SourceSheet`)**:
     - Smooth animated bottom sheet occupying ~70% screen height.
     - Document metadata badge and page reference (`PAGE 12`).
     - Quote block with cyan indicator border (`┃ "Refund requests..."`).
     - Relevance score meter and ASCII block progress bar (`████████████░░ 87%`).
     - Multi-citation tab switcher when multiple sources are cited.

---

## 🎨 Design System & Aesthetics

- **Background**: `#0A0A0F`
- **Surfaces**: `#12121A` & `#181826`
- **Primary Cyan**: `#22D3EE` (glows, borders, citations)
- **Secondary Purple**: `#A855F7` (OCR status, assistant accent)
- **Primary Text**: `#E5E5E5`
- **Muted Text**: `#8B8B95`
- **Warnings / Insufficient Info**: `#F59E0B`
- **Typography**: Monospace for data, tags, citations, documents; Sans-serif for conversational messages.

---

## 🚀 Getting Started

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Expo Development Server
```bash
npm start
# or
npx expo start
```

### 3. Run on Platforms
- **iOS Simulator**: Press `i` or `npm run ios`
- **Android Emulator**: Press `a` or `npm run android`
- **Web Browser**: Press `w` or `npm run web`
- **Physical Device**: Scan the QR code with Expo Go

---

## 📂 Project Structure

```text
frontend/
├── assets/
├── src/
│   ├── app/
│   │   ├── _layout.tsx       # Root provider & stack navigator
│   │   ├── index.tsx         # Auth redirect coordinator
│   │   ├── auth/
│   │   │   ├── _layout.tsx   # Auth stack
│   │   │   ├── login.tsx     # Login screen with validation
│   │   │   └── signup.tsx    # Signup screen with confirm password
│   │   └── app/
│   │       └── index.tsx     # Main DocuMind chat & RAG application
│   ├── components/
│   │   ├── DocuMindLogo.tsx   # Reusable brand logo (compact/large)
│   │   ├── GlassCard.tsx      # Dark translucent technical card
│   │   ├── PrimaryButton.tsx  # Accessible 44px min touch button
│   │   ├── IconButton.tsx     # Header icon button with cyan glow
│   │   ├── StatusBadge.tsx    # Document state badges with pulse animation
│   │   ├── DocumentRow.tsx    # Document item row with progress & selection
│   │   ├── ChatMessage.tsx    # Bubble renderer with interactive citations & warning state
│   │   ├── CitationChip.tsx   # Inline interactive citation pill [1]
│   │   ├── ChatInput.tsx      # Multiline keyboard-aware composer
│   │   ├── SourceSheet.tsx    # Bottom sheet citation inspection viewer
│   │   ├── DocumentsSheet.tsx # Bottom sheet knowledge base & uploader
│   │   └── LoadingDots.tsx    # Sequential purple bouncing dots
│   ├── constants/
│   │   └── theme.ts          # Central colors, fonts, spacing, radius
│   ├── context/
│   │   └── AppContext.tsx    # Unified state management (auth, docs, chat, sheets)
│   ├── data/
│   │   └── mockData.ts       # Realistic mock documents, citations, and Q&A
│   ├── hooks/
│   │   └── useDocuments.ts   # Document management hook
│   └── types/
│       └── index.ts          # TypeScript interfaces
└── package.json
```
