import { readdir, readFile, rm } from 'node:fs/promises';

const CODE_PATTERN =
  /\r?\n\r?\n([A-Za-z0-9-]+)\r?\n\r?\nEl código vence en (?:15|3) minutos/;

function decodeQuotedPrintable(message: string): string {
  const unfolded = message.replace(/=\r?\n/g, '');
  const bytes = unfolded.replace(/=([A-Fa-f0-9]{2})/g, (_, hex: string) =>
    String.fromCharCode(Number.parseInt(hex, 16)),
  );
  return Buffer.from(bytes, 'latin1').toString('utf8');
}

export async function waitForMailCode(
  directory: string,
  bodyMarker: string,
): Promise<string> {
  const deadline = Date.now() + 15_000;
  while (Date.now() < deadline) {
    const names = await readdir(directory).catch(() => []);
    const messages = await Promise.all(
      names.map(async (name) => ({
        name,
        text: await readFile(`${directory}/${name}`, 'utf8'),
      })),
    );
    const matching = messages
      .map(({ name, text }) => ({ name, text: decodeQuotedPrintable(text) }))
      .filter(({ text }) => text.includes(bodyMarker));
    if (matching.length === 1) {
      const message = matching[0];
      if (!message) continue;
      const code = CODE_PATTERN.exec(message.text)?.[1];
      if (code) {
        await rm(`${directory}/${message.name}`, { force: true });
        return code;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error('No se recibió un único correo con la estructura esperada.');
}

export async function waitForInvitationLink(
  directory: string,
  recipient: string,
): Promise<string> {
  const deadline = Date.now() + 15_000;
  const linkPattern =
    /https?:\/\/[^\s]+\/invitaciones\/activar\?token=[A-Za-z0-9_-]+/;
  while (Date.now() < deadline) {
    const names = await readdir(directory).catch(() => []);
    const messages = await Promise.all(
      names.map(async (name) => ({
        name,
        text: await readFile(`${directory}/${name}`, 'utf8'),
      })),
    );
    const matching = messages
      .map(({ name, text }) => ({ name, text: decodeQuotedPrintable(text) }))
      .filter(({ text }) => text.includes(recipient))
      .map(({ name, text }) => ({ name, link: linkPattern.exec(text)?.[0] }))
      .filter((message): message is { name: string; link: string } =>
        Boolean(message.link),
      );
    if (matching.length === 1) {
      const message = matching[0];
      if (message) {
        await rm(`${directory}/${message.name}`, { force: true });
        return message.link;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(
    'No se recibió un enlace de invitación para la persona esperada.',
  );
}
