import type { A } from "vitest/dist/reporters-w_64AS5f.js";

export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

export type User = {
    id: string;
    name: string;
    email: string;
    role: string;
    profile_image_url: string;
}

export type Params = {
        model: string;
        prompt: string;
        knowledge: {
            settings: {
                searchMode: string;
                useLimit: number;
                relevance: number;
                contentReordering: boolean;
                optimization: boolean;
            };
            items: string[];
        };
        tools: string[];
}

export type WorkflowApp = {
    id: string;
    name: string;
    description: string;
    params: Params | null;
}

export type Agent = {
    id: string;
    name: string;
    base_app_id: string;
    description: string;
    user_id: string;
    params: Params | null;
    user?: User;
    workflow_app?: Agent;
    access_control: any;
};