import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Folder, FileText, Image, File } from "lucide-react";

interface LasFile {
  id: string;
  filename: string;
  filepath: string;
  size: string;
  source: string;
  processed: boolean;
  createdAt: string;
}

interface OutputFile {
  id: string;
  filename: string;
  filepath: string;
  type: string;
  relatedLasFile?: string;
  createdAt: string;
}

interface FileBrowserProps {
  onImageSelect: (imageSrc: string) => void;
}

export default function FileBrowser({ onImageSelect }: FileBrowserProps) {
  const { data: lasFiles = [], isLoading: loadingLas } = useQuery<LasFile[]>({
    queryKey: ["/api/files/las"],
  });

  const { data: outputFiles = [], isLoading: loadingOutput } = useQuery<OutputFile[]>({
    queryKey: ["/api/files/output"],
  });

  const handleFileClick = (file: OutputFile) => {
    if (file.filename.endsWith('.png') || file.filename.endsWith('.jpg') || file.filename.endsWith('.jpeg')) {
      onImageSelect(`/api/files/output/${file.filename}`);
    }
  };

  const getFileIcon = (filename: string) => {
    if (filename.endsWith('.las')) {
      return <FileText className="w-4 h-4 text-blue-500" />;
    } else if (filename.endsWith('.png') || filename.endsWith('.jpg') || filename.endsWith('.jpeg')) {
      return <Image className="w-4 h-4 text-green-500" />;
    } else {
      return <File className="w-4 h-4 text-gray-500" />;
    }
  };

  const formatFileSize = (size: string) => {
    return size || "Unknown";
  };

  return (
    <div className="p-6">
      <h3 className="text-sm font-medium text-foreground mb-3">File Browser</h3>
      
      {/* Data Folder */}
      <div className="mb-4">
        <div className="flex items-center gap-2 mb-2">
          <Folder className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">data/</span>
          <span className="text-xs text-muted-foreground">({lasFiles.length} files)</span>
        </div>
        
        <ScrollArea className="ml-6 max-h-32">
          <div className="space-y-1">
            {loadingLas ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse flex items-center gap-2 p-2">
                    <div className="w-4 h-4 bg-muted rounded"></div>
                    <div className="h-4 bg-muted rounded flex-1"></div>
                    <div className="h-3 bg-muted rounded w-12"></div>
                  </div>
                ))}
              </div>
            ) : lasFiles.length === 0 ? (
              <p className="text-xs text-muted-foreground p-2">No LAS files found</p>
            ) : (
              lasFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2 p-2 hover:bg-muted rounded text-sm cursor-pointer transition-colors"
                  data-testid={`las-file-${file.filename}`}
                >
                  {getFileIcon(file.filename)}
                  <span className="flex-1 truncate">{file.filename}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">{formatFileSize(file.size)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>

      {/* Output Folder */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Folder className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">output/</span>
          <span className="text-xs text-muted-foreground">({outputFiles.length} files)</span>
        </div>
        
        <ScrollArea className="ml-6 max-h-32">
          <div className="space-y-1">
            {loadingOutput ? (
              <div className="space-y-2">
                {[1, 2].map((i) => (
                  <div key={i} className="animate-pulse flex items-center gap-2 p-2">
                    <div className="w-4 h-4 bg-muted rounded"></div>
                    <div className="h-4 bg-muted rounded flex-1"></div>
                    <div className="h-3 bg-muted rounded w-12"></div>
                  </div>
                ))}
              </div>
            ) : outputFiles.length === 0 ? (
              <p className="text-xs text-muted-foreground p-2">No output files generated yet</p>
            ) : (
              outputFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-2 p-2 hover:bg-muted rounded text-sm cursor-pointer transition-colors"
                  onClick={() => handleFileClick(file)}
                  data-testid={`output-file-${file.filename}`}
                >
                  {getFileIcon(file.filename)}
                  <span className="flex-1 truncate">{file.filename}</span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(file.createdAt).toLocaleDateString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
