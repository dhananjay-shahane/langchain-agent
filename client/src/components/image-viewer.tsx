import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { X, Download, ZoomIn, ZoomOut } from "lucide-react";

interface ImageViewerProps {
  imageSrc: string;
  onClose: () => void;
}

export default function ImageViewer({ imageSrc, onClose }: ImageViewerProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose]);

  const handleDownload = async () => {
    try {
      const response = await fetch(imageSrc);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const filename = imageSrc.split('/').pop() || 'image.png';
      
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to download image:", error);
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
      data-testid="image-viewer-overlay"
    >
      <div 
        className="bg-card rounded-lg max-w-4xl max-h-[90vh] overflow-hidden shadow-xl"
        onClick={(e) => e.stopPropagation()}
        data-testid="image-viewer-modal"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h3 className="text-lg font-semibold text-foreground">Plot Viewer</h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              data-testid="button-download-image"
            >
              <Download className="w-4 h-4 mr-2" />
              Download
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              data-testid="button-close-image-viewer"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        {/* Image */}
        <div className="p-4 max-h-[calc(90vh-80px)] overflow-auto">
          <img 
            src={imageSrc} 
            alt="Generated plot" 
            className="max-w-full h-auto mx-auto block"
            data-testid="image-viewer-image"
          />
        </div>
      </div>
    </div>
  );
}
