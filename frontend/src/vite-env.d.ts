/// \u003creference types="vite/client" /\u003e

interface ImportMetaEnv {
    readonly PROD: boolean;
    readonly DEV: boolean;
    readonly MODE: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
