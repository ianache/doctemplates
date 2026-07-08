import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";
import DocumentTypeListPage from "./pages/document-types/DocumentTypeListPage";
import DocumentTypeDetailPage from "./pages/document-types/DocumentTypeDetailPage";
import DocumentTypeCreatePage from "./pages/document-types/DocumentTypeCreatePage";
import ContentLibraryPage from "./pages/content/ContentLibraryPage";
import HtmlTemplateCreatePage from "./pages/content/HtmlTemplateCreatePage";
import HtmlTemplateDetailPage from "./pages/content/HtmlTemplateDetailPage";
import StaticPdfUploadPage from "./pages/content/StaticPdfUploadPage";
import StaticPdfDetailPage from "./pages/content/StaticPdfDetailPage";
import DocumentDesignListPage from "./pages/document-designs/DocumentDesignListPage";
import DocumentDesignCreatePage from "./pages/document-designs/DocumentDesignCreatePage";
import DocumentDesignDetailPage from "./pages/document-designs/DocumentDesignDetailPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />}>
        <Route index element={<Navigate to="/document-types" replace />} />
        <Route path="document-types" element={<DocumentTypeListPage />} />
        <Route path="document-types/new" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id" element={<DocumentTypeDetailPage />} />
        <Route path="document-designs" element={<DocumentDesignListPage />} />
        <Route path="document-designs/new" element={<DocumentDesignCreatePage />} />
        <Route path="document-designs/:id" element={<DocumentDesignDetailPage />} />
        <Route path="content" element={<ContentLibraryPage />}>
          <Route path="templates/new" element={<HtmlTemplateCreatePage />} />
          <Route path="templates/:id" element={<HtmlTemplateDetailPage />} />
          <Route path="static-pdfs/upload" element={<StaticPdfUploadPage />} />
          <Route path="static-pdfs/:id" element={<StaticPdfDetailPage />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
