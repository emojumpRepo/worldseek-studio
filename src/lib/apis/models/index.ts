import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { WorkflowApp, ApiResponse } from '$lib/types';

// 清理错误信息，去除HTML标签和过长的内容
const cleanErrorMessage = (errorMessage: string): string => {
	// 移除HTML标签
	const withoutHtml = errorMessage.replace(/<[^>]*>/g, '');
	
	// 移除多余的空白字符
	const withoutExtraWhitespace = withoutHtml.replace(/\s+/g, ' ').trim();
	
	// 如果错误信息太长，截取前200个字符
	if (withoutExtraWhitespace.length > 200) {
		return withoutExtraWhitespace.substring(0, 200) + '...';
	}
	
	// 如果是空白或太短，返回默认错误信息
	if (withoutExtraWhitespace.length < 3) {
		return '服务请求失败，请稍后重试';
	}
	
	return withoutExtraWhitespace;
};

export const getModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}
    console.log('res', res);
	return res;
};

// 获取工作空间智能体列表（仅当前用户的）
export const getWorkspaceModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/workspace`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}
    console.log('workspace models res', res);
	return res;
};

// 获取工作流应用
export const getWorkflowApps = async (token: string = '', sync: boolean = false): Promise<ApiResponse<WorkflowApp[]>> => {
	let error = null;

	// 构建URL，添加sync参数
	const url = new URL(`${WEBUI_API_BASE_URL}/workflows/`);
	if (sync) {
		url.searchParams.append('sync', 'true');
	}

	const res = await fetch(url.toString(), {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return { data: Array.isArray(json) ? json : [], success: true };
		})
		.catch((err: unknown) => {
			error = err;
			console.log('getWorkflowApps error:', err);
			const rawError = (err as Record<string, unknown>)?.detail || 
							 (err as Record<string, unknown>)?.message || 
							 '获取工作流失败';
			const errorMessage = cleanErrorMessage(String(rawError));
			return { data: [], success: false, error: errorMessage };
		});

	if (error) {
		console.error('getWorkflowApps捕获到错误:', error);
		const rawError = (error as Record<string, unknown>)?.detail || 
						 (error as Record<string, unknown>)?.message || 
						 '获取工作流失败';
		const errorMessage = cleanErrorMessage(String(rawError));
		return { data: [], success: false, error: errorMessage };
	}
	return res;
};

export const getBaseModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/base`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createNewModel = async (token: string, model: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(model)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/model?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const toggleModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/model/toggle?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateModelById = async (token: string, id: string, model: object) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/agent/update?${searchParams.toString()}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(model)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteModelById = async (token: string, id: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	const res = await fetch(`${WEBUI_API_BASE_URL}/agents/agent/delete?${searchParams.toString()}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteAllModels = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/models/delete/all`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
