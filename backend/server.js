import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import OpenAI from 'openai';

const app = express();
app.use(cors());
app.use(bodyParser.json());

// Leer la API key desde variables de entorno para no hardcodear secretos.
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY;
const OPENROUTER_BASE_URL = process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1';

if (!OPENROUTER_API_KEY) {
  console.error('Falta la API key. Define OPENROUTER_API_KEY (o OPENAI_API_KEY) en el entorno.');
  console.error('Ejemplo: export OPENROUTER_API_KEY=sk-or-...');
  process.exit(1);
}

const openai = new OpenAI({
  apiKey: OPENROUTER_API_KEY,
  baseURL: OPENROUTER_BASE_URL
});

app.post('/comando', async (req, res) => {
  const prompt = `Instrucción: ${req.body.mensaje}`;

  try {
    const completion = await openai.chat.completions.create({
      model: "deepseek/deepseek-r1-0528:free",  
      messages: [
        {
          role: "system",
          content: "Eres un traductor de instrucciones de red a comandos Cisco. Solo responde con el comando exacto. Nada más. Sin comillas, sin markdown, sin explicación."
        },
        {
          role: "user",
          content: prompt
        }
      ],
      temperature: 0,
      max_tokens: 50
    });

    const respuesta = completion.choices?.[0]?.message?.content?.trim() || "Sin respuesta válida";
    res.json({ respuesta });

  } catch (error) {
    // Mejor logging para depurar 401s u otros errores retornados por el upstream
    console.error('Error contacting OpenAI/OpenRouter API:');
    console.error('message:', error?.message);
    if (error?.status) console.error('status:', error.status);
    if (error?.error) console.error('error body:', error.error);

    // Reenviamos el estatus si viene del proveedor para que el frontend pueda conocerlo
    if (error?.status) {
      const message = error?.error?.message || error?.message || 'Error upstream';
      res.status(error.status).json({ respuesta: `Error upstream: ${message}` });
    } else {
      res.status(500).json({ respuesta: 'Error al contactar con OpenRouter API' });
    }
  }
});

app.listen(3000, () => console.log('✅ Backend corriendo en http://localhost:3000'));
