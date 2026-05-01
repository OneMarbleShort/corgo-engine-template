//
//  scenes/hellocorgo.c
//  Hello Corgo!.
//

#include "engine/corgo.h"
#include "engine/shortcuts/scene.h"

// Move to a component
static CE_TransformComponent* transformComponent = NULL;
static int xSpeed = 1;
static int ySpeed = 1;

CE_DECLARE_SCENE_CREATE_FUNCTION(HelloCorgo)
{
    CES_CREATE_ENTITY(parent);
    CES_ADD_COMPONENT_EPTR(parent, CE_TRANSFORM_COMPONENT, transformComponent);
    CES_ADD_COMPONENT_PTR(parent, CE_TEXT_LABEL_COMPONENT, textLabelComponent);
    
    // Set text and font
    CES_CHECK_RESULT(
        CE_TextLabelComponent_setStaticText(context, textLabelComponent, transformComponent, "Hello, Corgo Engine!"), 
        "Failed to set text for TextLabelComponent");

    CES_CHECK_RESULT(
         CE_TextLabelComponent_setFont(context, textLabelComponent, transformComponent, "/System/Fonts/Roobert-10-Bold.pft"), 
        "Failed to set font for TextLabelComponent");

    // Add to root of graph
    CES_ADD_TO_ROOT(parent);
        
    CES_CHECK_RESULT(
        CE_TransformComponent_setPosition(context, transformComponent, (CE_GetDisplayWidth(context)-transformComponent->m_width)/2, (CE_GetDisplayHeight(context)-transformComponent->m_height)/2),
        "Failed to set position for TransformComponent");
    
    return CE_OK;
}

CE_DECLARE_SCENE_RUN_FUNCTION(HelloCorgo)
{
    
    const uint16_t x = transformComponent->m_x + xSpeed;
    const uint16_t y = transformComponent->m_y + ySpeed;

    if (x <= 0 || x + transformComponent->m_width >= CE_GetDisplayWidth(context)) {
        xSpeed *= -1;
    }
    if (y <= 0 || y + transformComponent->m_height >= CE_GetDisplayHeight(context)) {
        ySpeed *= -1;
    }

    // Update transform component position
    CE_TransformComponent_setPosition(context, transformComponent, x, y);

    return CE_OK;
}

CE_DECLARE_SCENE_LOAD_DATA_FUNCTION(HelloCorgo)
{
    // Populate the scene data with the scene id and function pointers
    scene->m_id = "HelloCorgo";
    scene->m_createFunction = CE_SCENE_CREATE_FUNCTION(HelloCorgo);
    scene->m_runFunction = CE_SCENE_RUN_FUNCTION(HelloCorgo);
    scene->m_scriptDataComponentType = CE_INVALID_TYPE_ID;
    return CE_OK;
}
