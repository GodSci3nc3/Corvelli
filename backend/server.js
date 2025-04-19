import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import OpenAI from 'openai';

const app = express();
app.use(cors());
app.use(bodyParser.json());

const openai = new OpenAI({
  apiKey: '***REMOVED***',
  baseURL: 'https://openrouter.ai/api/v1'
});

app.post('/comando', async (req, res) => {
  const prompt = `Instrucción: ${req.body.mensaje}`;

  try {
    const completion = await openai.chat.completions.create({
      model: "deepseek/deepseek-chat",  
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
    console.error("Error:", error);
    res.status(500).json({ respuesta: "Error al contactar con OpenRouter API" });
  }
});

app.listen(3000, () => console.log('✅ Backend corriendo en http://localhost:3000'));
