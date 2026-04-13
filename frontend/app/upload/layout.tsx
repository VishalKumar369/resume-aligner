import { Sidebar } from "@/components/ui/Sidebar";
import { TopNavbar } from "@/components/ui/TopNavbar";

export default function UploadLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className="flex h-screen bg-background overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden">
                <TopNavbar title="New Analysis" />
                <main className="flex-1 overflow-y-auto">
                    {children}
                </main>
            </div>
        </div>
    );
}
