package com.example.lddc.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.launch

abstract class BaseViewModel : ViewModel() {

    protected val exceptionHandler = CoroutineExceptionHandler { _, throwable ->
        handleError(throwable)
    }

    private val _errorMessage = MutableSharedFlow<String>()

    private val _isLoading = MutableStateFlow(false)

    protected fun hideLoading() {
        _isLoading.value = false
    }

    protected fun handleError(throwable: Throwable) {
        hideLoading()
        viewModelScope.launch {
            _errorMessage.emit(throwable.message ?: "未知错误")
        }
    }

}
