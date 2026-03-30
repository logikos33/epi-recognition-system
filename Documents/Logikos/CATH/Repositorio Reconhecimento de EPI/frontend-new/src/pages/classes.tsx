import { Tag } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';

export function ClassesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Gerenciamento de Classes YOLO</h1>
        <p className="text-text-secondary mt-1">
          Configure e gerencie as classes de objetos para detecção
        </p>
      </div>

      <Card className="border border-border">
        <CardContent className="p-12 flex flex-col items-center justify-center text-center">
          <Tag className="w-16 h-16 text-text-muted mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Página em Desenvolvimento
          </h2>
          <p className="text-text-secondary max-w-md">
            Esta funcionalidade será implementada em breve. Você poderá gerenciar
            as classes YOLO, definir cores e configurar limiares de detecção.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
