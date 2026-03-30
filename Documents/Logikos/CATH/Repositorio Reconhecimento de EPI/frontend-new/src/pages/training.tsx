import { Brain } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';

export function TrainingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Treinamento de Modelo</h1>
        <p className="text-text-secondary mt-1">
          Gerencie o pipeline de treinamento do modelo YOLO
        </p>
      </div>

      <Card className="border border-border">
        <CardContent className="p-12 flex flex-col items-center justify-center text-center">
          <Brain className="w-16 h-16 text-text-muted mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">
            Página em Desenvolvimento
          </h2>
          <p className="text-text-secondary max-w-md">
            Esta funcionalidade será implementada em breve. Você poderá fazer upload
            de imagens, gerenciar anotações e treinar modelos personalizados.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
