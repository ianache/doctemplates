import { Navigate, Route, Routes } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import AuthenticatedShell from "./pages/AuthenticatedShell";
import DocumentTypeListPage from "./pages/document-types/DocumentTypeListPage";
import DocumentTypeDetailPage from "./pages/document-types/DocumentTypeDetailPage";
import DocumentTypeCreatePage from "./pages/document-types/DocumentTypeCreatePage";
import TemplatesPage from "./pages/content/TemplatesPage";
import StaticPdfsPage from "./pages/content/StaticPdfsPage";
import HtmlTemplateCreatePage from "./pages/content/HtmlTemplateCreatePage";
import HtmlTemplateDetailPage from "./pages/content/HtmlTemplateDetailPage";
import StaticPdfUploadPage from "./pages/content/StaticPdfUploadPage";
import StaticPdfDetailPage from "./pages/content/StaticPdfDetailPage";
import DocumentDesignListPage from "./pages/document-designs/DocumentDesignListPage";
import DocumentDesignCreatePage from "./pages/document-designs/DocumentDesignCreatePage";
import DocumentDesignDetailPage from "./pages/document-designs/DocumentDesignDetailPage";
import VersionHistoryPage from "./pages/document-designs/VersionHistoryPage";
import DocumentLibraryPage from "./pages/document-issuances/DocumentLibraryPage";
import DocumentIssuanceDetailPage from "./pages/document-issuances/DocumentIssuanceDetailPage";
import JobsMonitoringPage from "./pages/document-issuances/JobsMonitoringPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<AuthenticatedShell />}>
        <Route index element={<Navigate to="/document-types" replace />} />
        <Route path="document-types" element={<DocumentTypeListPage />} />
        <Route path="document-types/new" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id/edit" element={<DocumentTypeCreatePage />} />
        <Route path="document-types/:id" element={<DocumentTypeDetailPage />} />
        <Route path="document-designs" element={<DocumentDesignListPage />} />
        <Route path="document-designs/new" element={<DocumentDesignCreatePage />} />
        <Route path="document-designs/:id" element={<DocumentDesignDetailPage />} />
        <Route path="document-designs/:id/versions" element={<VersionHistoryPage />} />
        <Route path="document-issuances" element={<DocumentLibraryPage />} />
        <Route path="document-issuances/:id" element={<DocumentIssuanceDetailPage />} />
        <Route path="generation-jobs" element={<JobsMonitoringPage />} />
        <Route path="content/templates" element={<TemplatesPage />} />
        <Route path="content/templates/new" element={<HtmlTemplateCreatePage />} />
        <Route path="content/templates/:id" element={<HtmlTemplateDetailPage />} />
        <Route path="content/templates/:id/edit" element={<HtmlTemplateCreatePage />} />
        <Route path="content/static" element={<StaticPdfsPage />} />
        <Route path="content/static-pdfs/upload" element={<StaticPdfUploadPage />} />
        <Route path="content/static-pdfs/:id" element={<StaticPdfDetailPage />} />
      </Route>
    </Routes>
  );
}

export default App;
