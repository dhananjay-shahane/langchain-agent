import { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Upload, FileText, Trash2, MessageSquare, X } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";

interface PdfDocument {
  id: string;
  filename: string;
  originalName: string;
  size: string;
  pageCount: string | null;
  processed: boolean;
  uploadedAt: string;
}

interface PdfUploadProps {
  onDocumentSelect?: (document: PdfDocument) => void;
  selectedDocumentId?: string;
}

export default function PdfUpload({ onDocumentSelect, selectedDocumentId }: PdfUploadProps) {
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data: documents = [], isLoading } = useQuery<PdfDocument[]>({
    queryKey: ["/api/pdfs"],
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData();
      formData.append("pdf", file);

      // Use fetch directly for FormData uploads (don't use apiRequest which sets JSON headers)
      const response = await fetch("/api/pdfs/upload", {
        method: "POST",
        body: formData,
        // Don't set Content-Type header - let browser set it with boundary
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: "Upload failed" }));
        throw new Error(errorData.error || "Failed to upload PDF");
      }

      return await response.json();
    },
    onSuccess: (document) => {
      queryClient.invalidateQueries({ queryKey: ["/api/pdfs"] });
      toast({
        title: "PDF Uploaded",
        description: `${document.originalName} has been uploaded successfully.`,
      });
      setUploadProgress(0);
    },
    onError: (error: any) => {
      toast({
        title: "Upload Failed",
        description: error.message || "Failed to upload PDF document.",
        variant: "destructive",
      });
      setUploadProgress(0);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (documentId: string) => {
      const response = await apiRequest("DELETE", `/api/pdfs/${documentId}`);
      return await response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/pdfs"] });
      toast({
        title: "PDF Deleted",
        description: "Document has been deleted successfully.",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Delete Failed",
        description: error.message || "Failed to delete document.",
        variant: "destructive",
      });
    },
  });

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;

    const file = files[0];
    
    // Validate file type
    if (file.type !== "application/pdf") {
      toast({
        title: "Invalid File Type",
        description: "Please select a PDF file.",
        variant: "destructive",
      });
      return;
    }

    // Validate file size (max 10MB for now)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      toast({
        title: "File Too Large",
        description: "Please select a PDF file smaller than 10MB.",
        variant: "destructive",
      });
      return;
    }

    // Simulate upload progress
    setUploadProgress(10);
    setTimeout(() => setUploadProgress(50), 300);
    setTimeout(() => setUploadProgress(80), 600);
    
    uploadMutation.mutate(file);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const formatFileSize = (bytes: number | string) => {
    const size = typeof bytes === "string" ? parseInt(bytes) : bytes;
    if (size === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(size) / Math.log(k));
    return parseFloat((size / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <div className="space-y-6">
      {/* Upload Area */}
      <Card className="border-2 border-dashed border-muted-foreground/25">
        <CardContent className="p-6">
          <div
            className={`text-center transition-colors ${
              isDragging ? "bg-muted/50" : ""
            }`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Upload PDF Document</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Drag and drop a PDF file here, or click to select
            </p>
            <Button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadMutation.isPending}
              data-testid="upload-pdf-button"
            >
              {uploadMutation.isPending ? "Uploading..." : "Select PDF File"}
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={(e) => handleFileSelect(e.target.files)}
              className="hidden"
              data-testid="pdf-file-input"
            />
            {uploadProgress > 0 && uploadProgress < 100 && (
              <div className="mt-4">
                <Progress value={uploadProgress} className="w-full" />
                <p className="text-sm text-muted-foreground mt-2">
                  Uploading... {uploadProgress}%
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Document List */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Uploaded Documents</h3>
            <Badge variant="secondary" data-testid="document-count">
              {documents.length} documents
            </Badge>
          </div>
          
          <ScrollArea className="max-h-96">
            <div className="space-y-2">
              {isLoading ? (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="animate-pulse flex items-center gap-3 p-3">
                      <div className="w-10 h-10 bg-muted rounded"></div>
                      <div className="flex-1">
                        <div className="h-4 bg-muted rounded mb-2"></div>
                        <div className="h-3 bg-muted rounded w-1/2"></div>
                      </div>
                      <div className="w-8 h-8 bg-muted rounded"></div>
                    </div>
                  ))}
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                  <p>No PDF documents uploaded yet</p>
                  <p className="text-sm">Upload a PDF to start chatting with it</p>
                </div>
              ) : (
                documents.map((document) => (
                  <div
                    key={document.id}
                    className={`flex items-center gap-3 p-3 rounded-lg border transition-all hover:bg-muted/50 cursor-pointer ${
                      selectedDocumentId === document.id ? "border-primary bg-primary/5" : ""
                    }`}
                    onClick={() => onDocumentSelect?.(document)}
                    data-testid={`pdf-document-${document.id}`}
                  >
                    <div className="flex-shrink-0">
                      <FileText className="h-10 w-10 text-red-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{document.originalName}</p>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span>{formatFileSize(document.size)}</span>
                        {document.pageCount && (
                          <>
                            <span>•</span>
                            <span>{document.pageCount} pages</span>
                          </>
                        )}
                        <span>•</span>
                        <span>{formatDate(document.uploadedAt)}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant={document.processed ? "default" : "secondary"} className="text-xs">
                          {document.processed ? "Processed" : "Processing"}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {onDocumentSelect && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDocumentSelect(document);
                          }}
                          data-testid={`chat-with-${document.id}`}
                        >
                          <MessageSquare className="h-4 w-4" />
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMutation.mutate(document.id);
                        }}
                        disabled={deleteMutation.isPending}
                        data-testid={`delete-${document.id}`}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}